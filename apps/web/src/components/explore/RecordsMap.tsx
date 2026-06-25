"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import type maplibregl from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

type GL = typeof maplibregl;

export interface MapPoint {
  key: string;
  latitude: number;
  longitude: number;
  score: number;
  label: string;
}

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
  point: MapPoint,
  selected: boolean,
  onSelect: (key: string) => void,
): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.setAttribute("aria-label", point.label);
  const size = selected ? 18 : 11;
  Object.assign(element.style, {
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: "9999px",
    cursor: "pointer",
    background: markerColor(point.score),
    border: selected ? "2px solid #121212" : "1px solid #ffffff",
    boxShadow: "0 0 0 1px rgba(0,0,0,0.15)",
  });
  element.addEventListener("click", (event) => {
    event.stopPropagation();
    onSelect(point.key);
  });
  return element;
}

export function RecordsMap({
  points,
  selectedKey,
  onSelect,
}: {
  points: MapPoint[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const glRef = useRef<GL | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [ready, setReady] = useState(false);

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

  useEffect(() => {
    const map = mapRef.current;
    const gl = glRef.current;
    if (!map || !gl || !ready) return;
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = points.map((point) => {
      const element = markerElement(point, point.key === selectedKey, onSelect);
      return new gl.Marker({ element })
        .setLngLat([point.longitude, point.latitude])
        .addTo(map);
    });
  }, [ready, points, selectedKey, onSelect]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !selectedKey) return;
    const point = points.find((item) => item.key === selectedKey);
    if (point) {
      map.flyTo({ center: [point.longitude, point.latitude], zoom: 4 });
    }
  }, [ready, selectedKey, points]);

  return (
    <div
      ref={containerRef}
      className="h-[28rem] w-full overflow-hidden rounded-lg border border-hairline"
      role="region"
      aria-label="Map of flagged records"
    />
  );
}
