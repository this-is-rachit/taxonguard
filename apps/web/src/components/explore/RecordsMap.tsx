"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import type maplibregl from "maplibre-gl";
import { useCallback, useEffect, useRef, useState } from "react";

import { type LngLat } from "@/lib/geo";

type GL = typeof maplibregl;

export interface MapPoint {
  key: string;
  latitude: number;
  longitude: number;
  score: number;
  label: string;
}

const STYLE_URL =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://demotiles.maplibre.org/style.json";

const DRAW_SOURCE = "tg-draw";
const ACCENT = "#0079B5";

function markerColor(score: number): string {
  if (score >= 0.8) return "#D64545";
  if (score >= 0.5) return "#0079B5";
  return "#61A350";
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

function drawData(
  polygon: LngLat[] | null,
  draft: LngLat[],
  drawing: boolean,
): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = [];
  if (drawing) {
    if (draft.length >= 2) {
      features.push({
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: draft },
      });
    }
    for (const vertex of draft) {
      features.push({
        type: "Feature",
        properties: { kind: "vertex" },
        geometry: { type: "Point", coordinates: vertex },
      });
    }
  } else if (polygon && polygon.length >= 3) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [[...polygon, polygon[0]]] },
    });
  }
  return { type: "FeatureCollection", features };
}

export function RecordsMap({
  points,
  selectedKey,
  onSelect,
  polygon = null,
  onPolygonChange,
}: {
  points: MapPoint[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
  polygon?: LngLat[] | null;
  onPolygonChange?: (polygon: LngLat[] | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const glRef = useRef<GL | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const [ready, setReady] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<LngLat[]>([]);

  // Create the map once, on the client. Wait for the style to load before
  // marking ready, so draw layers can be added safely.
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
      map.on("load", () => {
        if (cancelled || !map) return;
        map.addSource(DRAW_SOURCE, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "tg-draw-fill",
          type: "fill",
          source: DRAW_SOURCE,
          filter: ["==", ["geometry-type"], "Polygon"],
          paint: { "fill-color": ACCENT, "fill-opacity": 0.12 },
        });
        map.addLayer({
          id: "tg-draw-line",
          type: "line",
          source: DRAW_SOURCE,
          filter: ["!=", ["geometry-type"], "Point"],
          paint: { "line-color": ACCENT, "line-width": 2 },
        });
        map.addLayer({
          id: "tg-draw-vertex",
          type: "circle",
          source: DRAW_SOURCE,
          filter: ["==", ["get", "kind"], "vertex"],
          paint: {
            "circle-radius": 4,
            "circle-color": "#ffffff",
            "circle-stroke-color": ACCENT,
            "circle-stroke-width": 2,
          },
        });
        mapRef.current = map;
        setReady(true);
      });
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
      glRef.current = null;
    };
  }, []);

  // Redraw record markers when points or the selection change.
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

  // Keep the draw overlay (committed polygon or in-progress draft) in sync.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource(DRAW_SOURCE) as
      | maplibregl.GeoJSONSource
      | undefined;
    source?.setData(drawData(polygon, draft, drawing));
  }, [ready, polygon, draft, drawing]);

  // While drawing, each click adds a vertex.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !drawing) return;
    const handler = (event: maplibregl.MapMouseEvent) => {
      setDraft((current) => [...current, [event.lngLat.lng, event.lngLat.lat]]);
    };
    map.on("click", handler);
    const canvas = map.getCanvas();
    canvas.style.cursor = "crosshair";
    return () => {
      map.off("click", handler);
      canvas.style.cursor = "";
    };
  }, [ready, drawing]);

  // Fly to the selected point.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !selectedKey) return;
    const point = points.find((item) => item.key === selectedKey);
    if (point)
      map.flyTo({ center: [point.longitude, point.latitude], zoom: 4 });
  }, [ready, selectedKey, points]);

  const fitToData = useCallback(() => {
    const map = mapRef.current;
    const gl = glRef.current;
    if (!map || !gl || points.length === 0) return;
    const bounds = new gl.LngLatBounds();
    for (const point of points)
      bounds.extend([point.longitude, point.latitude]);
    map.fitBounds(bounds, { padding: 48, maxZoom: 7, duration: 600 });
  }, [points]);

  const startDraw = () => {
    onPolygonChange?.(null);
    setDraft([]);
    setDrawing(true);
  };
  const finishDraw = () => {
    setDrawing(false);
    if (draft.length >= 3) onPolygonChange?.(draft);
    else onPolygonChange?.(null);
    setDraft([]);
  };
  const cancelDraw = () => {
    setDrawing(false);
    setDraft([]);
  };
  const clearArea = () => {
    onPolygonChange?.(null);
    setDraft([]);
  };

  const btn =
    "rounded-md border border-hairline bg-white px-2.5 py-1 text-xs font-bold text-ink shadow-sm hover:border-primary";

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="h-[28rem] w-full overflow-hidden rounded-lg border border-hairline"
        role="region"
        aria-label="Map of flagged records"
      />
      {onPolygonChange ? (
        <div className="pointer-events-none absolute left-3 top-3 flex flex-wrap gap-2">
          {drawing ? (
            <>
              <span className="pointer-events-auto rounded-md bg-ink/80 px-2.5 py-1 text-xs font-bold text-white">
                Click to add points
              </span>
              <button
                type="button"
                onClick={finishDraw}
                className={`pointer-events-auto ${btn}`}
              >
                Finish ({draft.length})
              </button>
              <button
                type="button"
                onClick={cancelDraw}
                className={`pointer-events-auto ${btn}`}
              >
                Cancel
              </button>
            </>
          ) : polygon ? (
            <button
              type="button"
              onClick={clearArea}
              className={`pointer-events-auto ${btn}`}
            >
              Clear area
            </button>
          ) : (
            <button
              type="button"
              onClick={startDraw}
              className={`pointer-events-auto ${btn}`}
            >
              Draw area
            </button>
          )}
          <button
            type="button"
            onClick={fitToData}
            className={`pointer-events-auto ${btn}`}
          >
            Fit to data
          </button>
        </div>
      ) : null}
    </div>
  );
}
