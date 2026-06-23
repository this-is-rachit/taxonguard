"""Draft GBIF annotation rules from flagged records.

A rule says, in GBIF's annotation form, that records of a taxon inside a geographic
polygon carry a controlled-vocabulary value. The polygon is the convex hull of the
flagged points, written as WKT; one or two points are buffered to a small valid
polygon. The default value is "suspicious", which is GBIF's default annotation
value. A confirmed rule is what gets written back to GBIF in Phase 6.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from shapely.geometry import MultiPoint

# Controlled vocabulary for the rule value. "suspicious" is the GBIF default.
SUSPICIOUS = "suspicious"
ALLOWED_VALUES: frozenset[str] = frozenset({SUSPICIOUS})

# A single point or a straight line has no area, so it is buffered by this many
# degrees to make a small but valid polygon (about one kilometre at the equator).
DEFAULT_BUFFER_DEG = 0.01


@dataclass(frozen=True)
class AnnotationRule:
    """A draft annotation: a taxon, a WKT polygon, and a controlled value."""

    taxon: str
    geometry_wkt: str
    value: str
    record_count: int

    def to_dict(self) -> dict[str, object]:
        """Return the rule as a plain dict for the annotation adapter (Phase 6)."""
        return {
            "taxon": self.taxon,
            "geometry": self.geometry_wkt,
            "annotation": self.value,
            "record_count": self.record_count,
        }


def build_wkt_polygon(
    points: Sequence[tuple[float, float]],
    *,
    buffer_deg: float = DEFAULT_BUFFER_DEG,
) -> str:
    """Return a WKT polygon covering the points, given as (latitude, longitude).

    The polygon is the convex hull of the points. A degenerate hull (a single
    point or a line) is buffered to a small valid polygon.
    """
    if not points:
        raise ValueError("at least one point is required to build a polygon")

    # Shapely and WKT use (x, y) = (longitude, latitude) order.
    geometry = MultiPoint([(longitude, latitude) for latitude, longitude in points]).convex_hull
    if geometry.geom_type != "Polygon":
        geometry = geometry.buffer(buffer_deg)
    return str(geometry.wkt)


def build_rule(
    taxon: str,
    points: Sequence[tuple[float, float]],
    *,
    value: str = SUSPICIOUS,
    buffer_deg: float = DEFAULT_BUFFER_DEG,
) -> AnnotationRule:
    """Build a draft annotation rule for a taxon over the flagged points.

    Points are (latitude, longitude). Raises ValueError on an empty point set or
    a value outside the controlled vocabulary.
    """
    if value not in ALLOWED_VALUES:
        raise ValueError(f"value must be one of {sorted(ALLOWED_VALUES)}, got {value!r}")
    if not points:
        raise ValueError("at least one point is required to build a rule")

    geometry_wkt = build_wkt_polygon(points, buffer_deg=buffer_deg)
    return AnnotationRule(
        taxon=taxon,
        geometry_wkt=geometry_wkt,
        value=value,
        record_count=len(points),
    )
