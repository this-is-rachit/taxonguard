from __future__ import annotations

import pytest
from shapely.geometry import Point
from shapely.wkt import loads as load_wkt

from taxonguard_core.explain.rule import (
    SUSPICIOUS,
    AnnotationRule,
    build_rule,
    build_wkt_polygon,
)


def test_polygon_covers_the_points() -> None:
    points = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0)]
    wkt = build_wkt_polygon(points)
    polygon = load_wkt(wkt)
    assert polygon.geom_type == "Polygon"
    # The hull should contain a point well inside the square (lon, lat order).
    assert polygon.contains(Point(5.0, 5.0))


def test_single_point_becomes_a_valid_polygon() -> None:
    wkt = build_wkt_polygon([(48.0, 2.0)])
    polygon = load_wkt(wkt)
    assert polygon.geom_type == "Polygon"
    assert polygon.area > 0.0


def test_two_points_become_a_valid_polygon() -> None:
    wkt = build_wkt_polygon([(0.0, 0.0), (1.0, 1.0)])
    polygon = load_wkt(wkt)
    assert polygon.geom_type == "Polygon"
    assert polygon.area > 0.0


def test_build_rule_defaults_to_suspicious() -> None:
    rule = build_rule("Rana temporaria", [(0.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
    assert isinstance(rule, AnnotationRule)
    assert rule.value == SUSPICIOUS
    assert rule.taxon == "Rana temporaria"
    assert rule.record_count == 3
    assert load_wkt(rule.geometry_wkt).geom_type == "Polygon"


def test_rule_to_dict_shape() -> None:
    rule = build_rule("Panthera leo", [(1.0, 2.0)])
    payload = rule.to_dict()
    assert payload["taxon"] == "Panthera leo"
    assert payload["annotation"] == SUSPICIOUS
    assert payload["record_count"] == 1
    assert isinstance(payload["geometry"], str)


def test_unknown_value_rejected() -> None:
    with pytest.raises(ValueError):
        build_rule("Rana temporaria", [(0.0, 0.0)], value="definitely_wrong")


def test_empty_points_rejected() -> None:
    with pytest.raises(ValueError):
        build_rule("Rana temporaria", [])
