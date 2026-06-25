import { describe, expect, it } from "vitest";

import { type LngLat, pointInPolygon } from "./geo";

const square: LngLat[] = [
  [0, 0],
  [10, 0],
  [10, 10],
  [0, 10],
];

describe("pointInPolygon", () => {
  it("returns true for a point inside", () => {
    expect(pointInPolygon([5, 5], square)).toBe(true);
  });

  it("returns false for a point outside", () => {
    expect(pointInPolygon([15, 5], square)).toBe(false);
    expect(pointInPolygon([-1, -1], square)).toBe(false);
  });

  it("returns false for a degenerate polygon", () => {
    expect(pointInPolygon([5, 5], [])).toBe(false);
    expect(
      pointInPolygon(
        [5, 5],
        [
          [0, 0],
          [10, 10],
        ],
      ),
    ).toBe(false);
  });

  it("handles a concave polygon", () => {
    const concave: LngLat[] = [
      [0, 0],
      [10, 0],
      [10, 10],
      [5, 5],
      [0, 10],
    ];
    expect(pointInPolygon([1, 5], concave)).toBe(true);
    expect(pointInPolygon([5, 8], concave)).toBe(false);
  });
});
