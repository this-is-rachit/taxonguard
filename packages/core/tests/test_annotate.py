from __future__ import annotations

import base64

import httpx
import pytest

from taxonguard_core.annotate.client import (
    ANNOTATION_UI_URL,
    AnnotationError,
    GbifAnnotationClient,
    NullAnnotationClient,
    manual_instructions,
)
from taxonguard_core.explain.rule import build_rule

# A small confirmed rule to submit. Points are (latitude, longitude).
_RULE = build_rule("Rana temporaria", [(0.0, 0.0), (1.0, 1.0), (0.0, 1.0)])

# The created-rule id the mock annotation server returns.
_CREATED_ID = 4242
# The taxon key the mock species-match endpoint returns.
_TAXON_KEY = 2431885


def _mock_client(record: dict[str, object] | None = None) -> httpx.Client:
    """An httpx client whose transport serves both GBIF endpoints with no network.

    If ``record`` is given, the captured POST request is stored in it so a test can
    assert the exact request shape.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/species/match"):
            return httpx.Response(200, json={"usageKey": _TAXON_KEY, "matchType": "EXACT"})
        if request.url.path.endswith("/rule") and request.method == "POST":
            if record is not None:
                record["method"] = request.method
                record["path"] = request.url.path
                record["auth"] = request.headers.get("authorization", "")
                record["body"] = request.content.decode("utf-8")
            return httpx.Response(
                200,
                json={"id": _CREATED_ID, "geometry": "POLYGON", "annotation": "SUSPICIOUS"},
            )
        return httpx.Response(404, json={})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_null_client_returns_manual_fallback() -> None:
    result = NullAnnotationClient().submit(_RULE)
    assert result.submitted is False
    assert result.manual is True
    assert result.rule_id is None
    assert result.ui_url == ANNOTATION_UI_URL
    assert result.manual_instructions is not None
    # The manual text names the taxon, the value, and the polygon to paste.
    assert "Rana temporaria" in result.manual_instructions
    assert "SUSPICIOUS" in result.manual_instructions
    assert "POLYGON" in result.manual_instructions


def test_manual_instructions_contains_wkt_and_taxon() -> None:
    text = manual_instructions(_RULE)
    assert _RULE.geometry_wkt in text
    assert "Rana temporaria" in text
    assert ANNOTATION_UI_URL in text


def test_gbif_client_posts_expected_request_shape() -> None:
    record: dict[str, object] = {}
    with _mock_client(record) as client:
        gbif = GbifAnnotationClient(username="alice", password="secret", client=client)
        result = gbif.submit(_RULE)

    # The request went to the annotation /rule endpoint as a POST.
    assert record["method"] == "POST"
    assert str(record["path"]).endswith("/occurrence/experimental/annotation/rule")

    # HTTP Basic Auth carried the configured credentials.
    expected = "Basic " + base64.b64encode(b"alice:secret").decode("ascii")
    assert record["auth"] == expected

    # The JSON body carries the WKT geometry, the resolved taxon key, and the
    # canonical upper-case annotation term.
    body = str(record["body"])
    assert _RULE.geometry_wkt in body
    assert str(_TAXON_KEY) in body
    assert "SUSPICIOUS" in body

    # The response is parsed into a submitted result with the created id and URLs.
    assert result.submitted is True
    assert result.manual is False
    assert result.rule_id == _CREATED_ID
    assert result.rule_url is not None
    assert result.rule_url.endswith(f"/rule/{_CREATED_ID}")
    assert result.ui_url == ANNOTATION_UI_URL


def test_gbif_client_uppercases_the_annotation_value() -> None:
    record: dict[str, object] = {}
    with _mock_client(record) as client:
        # value defaults to the lower-case controlled term "suspicious".
        assert _RULE.value == "suspicious"
        GbifAnnotationClient(username="u", password="p", client=client).submit(_RULE)
    assert '"annotation":"SUSPICIOUS"' in str(record["body"])


def test_gbif_client_uses_injected_resolver_without_network() -> None:
    calls: list[str] = []

    def resolver(name: str) -> int:
        calls.append(name)
        return 777

    record: dict[str, object] = {}
    with _mock_client(record) as client:
        gbif = GbifAnnotationClient(
            username="u", password="p", client=client, resolve_taxon_key=resolver
        )
        gbif.submit(_RULE)

    assert calls == ["Rana temporaria"]
    assert "777" in str(record["body"])


def test_gbif_client_raises_on_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/rule"):
            return httpx.Response(500, json={"message": "boom"})
        return httpx.Response(404, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        gbif = GbifAnnotationClient(
            username="u", password="p", client=client, resolve_taxon_key=lambda _: 1
        )
        with pytest.raises(AnnotationError):
            gbif.submit(_RULE)


def test_gbif_client_raises_when_taxon_match_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # The match endpoint errors, so the key cannot be resolved.
        return httpx.Response(503, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        gbif = GbifAnnotationClient(username="u", password="p", client=client)
        with pytest.raises(AnnotationError):
            gbif.submit(_RULE)
