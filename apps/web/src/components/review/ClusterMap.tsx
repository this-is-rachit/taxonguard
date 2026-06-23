"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import type maplibregl from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

import { type ClusterSummary } from "@/lib/api";

type GL = typeof maplibregl;

// MapLibre's demo style is free and needs no API key, so the map works for any
// reviewer with no setup. Override it with NEXT_PUBLIC_MAP_STYLE_URL if desired.
const STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://demotiles.maplibre.org/style.json";

function markerColor(score: number): string {
  if (score >= 0.8) return "#D64545"; // error red
  if (score >= 0.5) return "#0079B5"; // secondary blue
  return "#61A350"; // primary green
}

function markerElement(
  cluster: ClusterSummary,
  selected: boolean,
  onSelect: (id: string) => void,
): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.setAttribute("aria-label", `${cluster.taxon} cluster`);
  const size = selected ? 18 : 12;
  Object.assign(element.style, {
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: "9999px",
    cursor: "pointer",
    background: markerColor(cluster.max_score),
    border: selected ? "2px solid #121212" : "1px solid #ffffff",
    boxShadow: "0 0 0 1px rgba(0,0,0,0.15)",
  });
  element.addEventListener("click", (event) => {
    event.stopPropagation();
    onSelect(cluster.cluster_id);
  });
  return element;
}

export function ClusterMap({
  clusters,
  selectedId,
  onSelect,
}: {
  clusters: ClusterSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const glRef = useRef<GL | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [ready, setReady] = useState(false);

  // Load MapLibre on the client only, so the module is never imported during
  // server rendering, and create the map once.
  useEffect(() => {
    let cancelled = false;
    let map: maplibregl.Map | null = null;
    void (async () => {
      const gl = (await import("maplibre-gl")).default;
      if (cancelled || !containerRef.current) return;
      glRef.current = gl;
      map = new gl.Map({
        container: containerRef.current,
        style: STYLE_URL,
        center: [0, 20],
        zoom: 1,
      });
      map.addControl(new gl.NavigationControl(), "top-right");
      mapRef.current = map;
      setReady(true);
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
      glRef.current = null;
    };
  }, []);

  // Redraw markers when the clusters or the selection change.
  useEffect(() => {
    const map = mapRef.current;
    const gl = glRef.current;
    if (!map || !gl || !ready) return;
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = clusters.map((cluster) => {
      const element = markerElement(
        cluster,
        cluster.cluster_id === selectedId,
        onSelect,
      );
      return new gl.Marker({ element })
        .setLngLat([cluster.longitude, cluster.latitude])
        .addTo(map);
    });
  }, [ready, clusters, selectedId, onSelect]);

  // Fly to the selected cluster.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !selectedId) return;
    const cluster = clusters.find((item) => item.cluster_id === selectedId);
    if (cluster) {
      map.flyTo({ center: [cluster.longitude, cluster.latitude], zoom: 4 });
    }
  }, [ready, selectedId, clusters]);

  return (
    <div
      ref={containerRef}
      className="h-80 w-full overflow-hidden rounded-lg border border-hairline"
      role="region"
      aria-label="Map of flagged clusters"
    />
  );
}
