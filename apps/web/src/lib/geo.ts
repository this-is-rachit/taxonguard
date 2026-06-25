// Minimal geometry helpers for the map's draw-area filter. Dependency-free so no
// lockfile changes: a standard ray-casting point-in-polygon test.

export type LngLat = [number, number];

// True when [lng, lat] falls inside the polygon (an open ring of [lng, lat]
// pairs; the closing edge back to the first point is implied).
export function pointInPolygon(point: LngLat, polygon: LngLat[]): boolean {
  if (polygon.length < 3) return false;
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersects =
      yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}
