"use client";

import { useEffect, useMemo, useState } from "react";

import { type MapPoint, RecordsMap } from "@/components/explore/RecordsMap";
import { WriteBackResult } from "@/components/explore/WriteBackResult";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { SuspicionMeter } from "@/components/ui/SuspicionMeter";
import { EmptyState } from "@/components/ui/States";
import { type CleanRecord, type CleanSummary } from "@/lib/api";
import { type LngLat, pointInPolygon } from "@/lib/geo";
import { useAnnotate } from "@/lib/queries";
import { REASON_META, reasonLabel } from "@/lib/reasons";

const REASON_ORDER = [
  "realm_mismatch",
  "zero_coordinates",
  "equal_coordinates",
  "gridded_coordinates",
  "institution_coordinates",
  "environmental_outlier",
];

type View = "map" | "table" | "summary";

function recordKey(record: CleanRecord, index: number): string {
  return record.gbif_id != null ? String(record.gbif_id) : `row-${index}`;
}

function FacetRail({
  counts,
  total,
  activeReasons,
  toggleReason,
  minScore,
  setMinScore,
  onReset,
}: {
  counts: Record<string, number>;
  total: number;
  activeReasons: Set<string>;
  toggleReason: (code: string) => void;
  minScore: number;
  setMinScore: (value: number) => void;
  onReset: () => void;
}) {
  const present = REASON_ORDER.filter((code) => (counts[code] ?? 0) > 0);
  return (
    <aside className="w-full shrink-0 md:w-64">
      <div className="rounded-lg border border-hairline bg-white p-sm">
        <div className="flex items-center justify-between">
          <p className="text-xs font-bold uppercase tracking-wide text-muted">
            Filters
          </p>
          <button
            type="button"
            onClick={onReset}
            className="text-xs font-bold text-primary hover:underline"
          >
            Reset
          </button>
        </div>

        <div className="mt-4">
          <label
            htmlFor="score-threshold"
            className="text-xs font-bold text-ink"
          >
            Minimum suspicion: {minScore.toFixed(2)}
          </label>
          <input
            id="score-threshold"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minScore}
            onChange={(event) => setMinScore(Number(event.target.value))}
            className="mt-2 w-full accent-secondary"
          />
          <p className="mt-1 text-xs text-muted">
            {total} record{total === 1 ? "" : "s"} at or above this score.
          </p>
        </div>

        <div className="mt-5">
          <p className="text-xs font-bold text-ink">Reason</p>
          <ul className="mt-2 flex flex-col gap-1">
            {present.length === 0 ? (
              <li className="text-xs text-muted">
                No reasons at this threshold.
              </li>
            ) : (
              present.map((code) => {
                const active = activeReasons.has(code);
                return (
                  <li key={code}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => toggleReason(code)}
                      className={`flex w-full items-center justify-between gap-2 rounded-md border px-2 py-1.5 text-left text-xs ${
                        active
                          ? "border-secondary bg-secondary/5 text-ink"
                          : "border-hairline text-muted hover:border-primary"
                      }`}
                    >
                      <span>{reasonLabel(code)}</span>
                      <span className="tabular-nums">{counts[code] ?? 0}</span>
                    </button>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      </div>
    </aside>
  );
}

function SummaryView({ summary }: { summary: CleanSummary }) {
  const max = Math.max(1, ...summary.issues.map((issue) => issue.count));
  return (
    <div className="rounded-lg border border-hairline bg-white p-md">
      <div className="flex flex-wrap items-end gap-10">
        <div>
          <p className="text-3xl font-semibold tabular-nums text-ink">
            {summary.total_records}
          </p>
          <p className="mt-1 text-sm text-muted">Records scanned</p>
        </div>
        <div>
          <p className="text-3xl font-semibold tabular-nums text-error">
            {summary.flagged_records}
          </p>
          <p className="mt-1 text-sm text-muted">Flagged as suspect</p>
        </div>
        <div>
          <p className="text-3xl font-semibold tabular-nums text-ink">
            {summary.clean_records}
          </p>
          <p className="mt-1 text-sm text-muted">No issue found</p>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wide text-muted">
          Checks run
        </span>
        {summary.checks_run.map((check) => (
          <Badge key={check} tone="primary">
            {check}
          </Badge>
        ))}
      </div>

      {summary.issues.length > 0 ? (
        <div className="mt-6">
          <p className="text-xs font-bold uppercase tracking-wide text-muted">
            Issues by type
          </p>
          <ul className="mt-3 flex flex-col gap-2">
            {summary.issues.map((issue) => (
              <li key={issue.label} className="flex items-center gap-3">
                <span className="w-64 shrink-0 text-sm text-ink">
                  {issue.label}
                </span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-hairline">
                  <span
                    className="block h-full bg-secondary"
                    style={{ width: `${(issue.count / max) * 100}%` }}
                  />
                </span>
                <span className="w-10 shrink-0 text-right text-sm tabular-nums text-muted">
                  {issue.count}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted">
          No suspicious records found in the sample checked.
        </p>
      )}
    </div>
  );
}

function RecordTable({
  records,
  selectedKey,
  onSelect,
  showTaxon,
}: {
  records: { key: string; record: CleanRecord }[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
  showTaxon: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-hairline">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-hairline text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-3 py-2 font-bold">ID</th>
            {showTaxon ? <th className="px-3 py-2 font-bold">Taxon</th> : null}
            <th className="px-3 py-2 font-bold">Latitude</th>
            <th className="px-3 py-2 font-bold">Longitude</th>
            <th className="px-3 py-2 font-bold">Score</th>
            <th className="px-3 py-2 font-bold">Reasons</th>
          </tr>
        </thead>
        <tbody>
          {records.map(({ key, record }) => (
            <tr
              key={key}
              onClick={() => onSelect(key)}
              className={`cursor-pointer border-b border-hairline last:border-0 ${
                key === selectedKey ? "bg-secondary/5" : "hover:bg-panel"
              }`}
            >
              <td className="px-3 py-2 tabular-nums text-muted">
                {record.gbif_id ?? "-"}
              </td>
              {showTaxon ? (
                <td className="px-3 py-2 italic text-ink">
                  {record.scientific_name ?? "-"}
                </td>
              ) : null}
              <td className="px-3 py-2 tabular-nums text-ink">
                {record.latitude.toFixed(4)}
              </td>
              <td className="px-3 py-2 tabular-nums text-ink">
                {record.longitude.toFixed(4)}
              </td>
              <td className="px-3 py-2">
                <SuspicionMeter score={record.suspicion_score} />
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  {record.reasons.map((code) => (
                    <Badge key={code}>{reasonLabel(code)}</Badge>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailPanel({ record }: { record: CleanRecord }) {
  return (
    <div className="rounded-lg border border-hairline bg-white p-sm">
      <p className="text-sm font-bold italic text-ink">
        {record.scientific_name ?? "Record"}
      </p>
      <div className="mt-2">
        <SuspicionMeter score={record.suspicion_score} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <dt className="text-muted">Latitude</dt>
        <dd className="tabular-nums text-ink">{record.latitude.toFixed(5)}</dd>
        <dt className="text-muted">Longitude</dt>
        <dd className="tabular-nums text-ink">{record.longitude.toFixed(5)}</dd>
        <dt className="text-muted">Confidence</dt>
        <dd className="tabular-nums text-ink">
          {record.confidence.toFixed(2)}
        </dd>
      </dl>

      <p className="mt-4 text-xs font-bold uppercase tracking-wide text-muted">
        Why it is flagged
      </p>
      <ul className="mt-2 flex flex-col gap-2">
        {record.reasons.length === 0 ? (
          <li className="text-sm text-muted">
            No issue found; this record looks plausible.
          </li>
        ) : (
          record.reasons.map((code) => (
            <li key={code} className="text-sm text-ink">
              <span className="font-bold">{reasonLabel(code)}.</span>{" "}
              <span className="text-muted">
                {REASON_META[code]?.description ?? ""}
              </span>
            </li>
          ))
        )}
      </ul>

      {record.gbif_id != null ? (
        <a
          href={`https://www.gbif.org/occurrence/${record.gbif_id}`}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-block text-sm font-bold text-primary hover:underline"
        >
          View this record on GBIF
        </a>
      ) : null}
    </div>
  );
}

export function RecordsExplorer({
  records,
  summary,
  taxonLabel,
  truncated = false,
  showTaxon = false,
  annotateTaxon,
}: {
  records: CleanRecord[];
  summary: CleanSummary;
  taxonLabel?: string;
  truncated?: boolean;
  showTaxon?: boolean;
  annotateTaxon?: string;
}) {
  const [minScore, setMinScore] = useState(0.5);
  const [activeReasons, setActiveReasons] = useState<Set<string>>(new Set());
  const [view, setView] = useState<View>("table");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [polygon, setPolygon] = useState<LngLat[] | null>(null);
  const annotate = useAnnotate();

  const keyed = useMemo(
    () =>
      records.map((record, index) => ({
        key: recordKey(record, index),
        record,
      })),
    [records],
  );

  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const { record } of keyed) {
      if (record.suspicion_score < minScore) continue;
      for (const code of record.reasons) {
        result[code] = (result[code] ?? 0) + 1;
      }
    }
    return result;
  }, [keyed, minScore]);

  const filtered = useMemo(
    () =>
      keyed.filter(
        ({ record }) =>
          record.suspicion_score >= minScore &&
          (activeReasons.size === 0 ||
            record.reasons.some((code) => activeReasons.has(code))) &&
          (polygon === null ||
            pointInPolygon([record.longitude, record.latitude], polygon)),
      ),
    [keyed, minScore, activeReasons, polygon],
  );

  const points: MapPoint[] = useMemo(
    () =>
      filtered.map(({ key, record }) => ({
        key,
        latitude: record.latitude,
        longitude: record.longitude,
        score: record.suspicion_score,
        label: `${record.scientific_name ?? "record"} (${record.suspicion_score.toFixed(2)})`,
      })),
    [filtered],
  );

  const selected = filtered.find((item) => item.key === selectedKey)?.record;

  function toggleReason(code: string) {
    setActiveReasons((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  const { reset: resetAnnotate } = annotate;
  // Clear a previous proposal whenever the filtered set changes, so the result
  // shown always matches the records currently in view.
  useEffect(() => {
    resetAnnotate();
  }, [resetAnnotate, minScore, activeReasons, polygon]);

  const annotatePoints = filtered.map(({ record }) => ({
    latitude: record.latitude,
    longitude: record.longitude,
  }));

  return (
    <div className="mt-6 flex flex-col gap-6 md:flex-row">
      <FacetRail
        counts={counts}
        total={filtered.length}
        activeReasons={activeReasons}
        toggleReason={toggleReason}
        minScore={minScore}
        setMinScore={setMinScore}
        onReset={() => {
          setMinScore(0.5);
          setActiveReasons(new Set());
          setPolygon(null);
        }}
      />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted">
            {taxonLabel ? (
              <span className="font-bold text-ink">{taxonLabel}</span>
            ) : null}
            {taxonLabel ? " — " : ""}
            {filtered.length} shown
            {truncated ? " (sample)" : ""}
            {polygon ? (
              <button
                type="button"
                onClick={() => setPolygon(null)}
                className="ml-3 rounded-full bg-panel px-2 py-0.5 text-xs font-bold text-primary hover:underline"
              >
                Area filter on · clear
              </button>
            ) : null}
          </p>
          <div
            role="tablist"
            aria-label="View"
            className="flex overflow-hidden rounded-md border border-hairline"
          >
            {(["table", "map", "summary"] as View[]).map((option) => (
              <button
                key={option}
                role="tab"
                aria-selected={view === option}
                onClick={() => setView(option)}
                className={`px-3 py-1.5 text-xs font-bold capitalize ${
                  view === option
                    ? "bg-secondary text-white"
                    : "bg-white text-muted hover:text-ink"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>

        {annotateTaxon ? (
          <div className="mt-3 rounded-lg border border-hairline bg-panel p-sm">
            <p className="text-xs font-bold uppercase tracking-wide text-muted">
              Write back to GBIF
            </p>
            <p className="mt-1 text-sm leading-6 text-muted">
              Propose a rule marking the {filtered.length} record
              {filtered.length === 1 ? "" : "s"} shown as{" "}
              <span className="font-bold text-ink">suspicious</span>, over the
              area they cover. With GBIF credentials this is published to
              GBIF&apos;s annotation system; without them you get the exact rule
              to create by hand.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button
                onClick={() =>
                  annotate.mutate({
                    taxon: annotateTaxon,
                    points: annotatePoints,
                  })
                }
                disabled={annotatePoints.length === 0 || annotate.isPending}
              >
                {annotate.isPending ? "Proposing..." : "Propose a GBIF rule"}
              </Button>
              {annotatePoints.length === 0 ? (
                <span className="text-xs text-muted">
                  Adjust the filters to include at least one record.
                </span>
              ) : null}
            </div>
            {annotate.isError ? (
              <p className="mt-2 text-sm text-error">
                Could not propose the rule. Check that the API is running and
                try again.
              </p>
            ) : null}
            {annotate.data ? (
              <div className="mt-3">
                <WriteBackResult
                  written={annotate.data.written_to_gbif}
                  annotationUrl={annotate.data.annotation_url}
                  manualInstructions={annotate.data.manual_instructions}
                  detail={annotate.data.detail}
                />
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="mt-3">
          {view === "summary" ? (
            <SummaryView summary={summary} />
          ) : view === "map" ? (
            <RecordsMap
              points={points}
              selectedKey={selectedKey}
              onSelect={setSelectedKey}
              polygon={polygon}
              onPolygonChange={setPolygon}
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="Nothing matches these filters"
              hint="Lower the minimum suspicion, clear the reason filters, or clear the drawn area."
            />
          ) : (
            <RecordTable
              records={filtered}
              selectedKey={selectedKey}
              onSelect={setSelectedKey}
              showTaxon={showTaxon}
            />
          )}
        </div>

        {selected && view !== "summary" ? (
          <div className="mt-4">
            <DetailPanel record={selected} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
