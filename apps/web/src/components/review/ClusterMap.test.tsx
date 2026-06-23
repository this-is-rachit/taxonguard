import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { type ClusterSummary } from "@/lib/api";

import { ClusterMap } from "./ClusterMap";

vi.mock("maplibre-gl", () => {
  const Marker = vi.fn(() => ({
    setLngLat: vi.fn().mockReturnThis(),
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
  }));
  const Map = vi.fn(() => ({
    addControl: vi.fn(),
    remove: vi.fn(),
    flyTo: vi.fn(),
  }));
  const NavigationControl = vi.fn();
  return { default: { Map, Marker, NavigationControl } };
});

function cluster(id: string, lat: number, lon: number): ClusterSummary {
  return {
    cluster_id: id,
    taxon: "Test fox",
    count: 1,
    max_score: 0.9,
    mean_score: 0.9,
    latitude: lat,
    longitude: lon,
    reason_counts: { realm_mismatch: 1 },
    explanation: "Flagged.",
    decision: null,
  };
}

describe("ClusterMap", () => {
  it("renders an accessible map region", () => {
    render(<ClusterMap clusters={[]} selectedId={null} onSelect={vi.fn()} />);
    expect(
      screen.getByRole("region", { name: "Map of flagged clusters" }),
    ).toBeInTheDocument();
  });

  it("creates one marker per cluster once the map is ready", async () => {
    const maplibregl = (await import("maplibre-gl")).default;
    render(
      <ClusterMap
        clusters={[cluster("a", 1, 2), cluster("b", 3, 4)]}
        selectedId={null}
        onSelect={vi.fn()}
      />,
    );
    await waitFor(() => expect(maplibregl.Marker).toHaveBeenCalledTimes(2));
  });
});
