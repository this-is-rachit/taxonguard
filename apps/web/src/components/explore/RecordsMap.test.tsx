import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { type MapPoint, RecordsMap } from "./RecordsMap";

vi.mock("maplibre-gl", () => {
  const Marker = vi.fn(() => ({
    setLngLat: vi.fn().mockReturnThis(),
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
  }));
  const Map = vi.fn(() => ({
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    getSource: vi.fn(),
    getCanvas: vi.fn(() => ({ style: {} })),
    on: vi.fn((event: string, cb: () => void) => {
      if (event === "load") cb();
    }),
    off: vi.fn(),
    remove: vi.fn(),
    flyTo: vi.fn(),
    fitBounds: vi.fn(),
  }));
  const NavigationControl = vi.fn();
  const LngLatBounds = vi.fn(() => ({ extend: vi.fn() }));
  return { default: { Map, Marker, NavigationControl, LngLatBounds } };
});

function point(key: string, lat: number, lon: number): MapPoint {
  return { key, latitude: lat, longitude: lon, score: 0.9, label: key };
}

describe("RecordsMap", () => {
  it("renders an accessible map region with the default label", () => {
    render(<RecordsMap points={[]} selectedKey={null} onSelect={vi.fn()} />);
    expect(
      screen.getByRole("region", { name: "Map of flagged records" }),
    ).toBeInTheDocument();
  });

  it("accepts a custom aria-label (used by the Review screen)", () => {
    render(
      <RecordsMap
        points={[]}
        selectedKey={null}
        onSelect={vi.fn()}
        ariaLabel="Map of flagged clusters"
      />,
    );
    expect(
      screen.getByRole("region", { name: "Map of flagged clusters" }),
    ).toBeInTheDocument();
  });

  it("creates one marker per point once the map is ready", async () => {
    const maplibregl = (await import("maplibre-gl")).default;
    render(
      <RecordsMap
        points={[point("a", 1, 2), point("b", 3, 4)]}
        selectedKey={null}
        onSelect={vi.fn()}
      />,
    );
    await waitFor(() => expect(maplibregl.Marker).toHaveBeenCalledTimes(2));
  });
});
