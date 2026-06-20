from taxonguard_core import __version__, health


def test_version_is_set() -> None:
    assert __version__ == "0.1.0"


def test_health_payload() -> None:
    payload = health()
    assert payload["package"] == "taxonguard-core"
    assert payload["status"] == "ok"
