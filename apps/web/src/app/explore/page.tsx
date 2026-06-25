"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Logo } from "@/components/Logo";
import { type MapPoint, RecordsMap } from "@/components/explore/RecordsMap";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { SuspicionMeter } from "@/components/ui/SuspicionMeter";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { type CleanRecord, type SpeciesScoreReport } from "@/lib/api";
import { REASON_META, reasonLabel } from "@/lib/reasons";
import { useSpeciesScore, useSpeciesSuggest } from "@/lib/queries";

const NAV = [
  { label: "Explore", href: "/explore" },
  { label: "Review", href: "/review" },
  { label: "Clean my data", href: "/clean" },
];

const REASON_ORDER = [
  "realm_mismatch",
  "zero_coordinates",
  "equal_coordinates",
  "gridded_coordinates",
  "institution_coordinates",
  "environmental_outlier",
];

const EXAMPLES = [
  "Rana temporaria",
  "Vulpes lagopus",
  "Panthera leo",
  "Bradypus variegatus",
];

type View = "map" | "table" | "summary";

function recordKey(record: CleanRecord, index: number): string {
  return record.gbif_id != null ? String(record.gbif_id) : `row-${index}`;
}

function SearchBar({ onPick }: { onPick: (name: string) => void }) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(timer);
  }, [query]);

  const suggest = useSpeciesSuggest(debounced);
  const suggestions = suggest.data ?? [];

  function pick(name: string) {
    setQuery(name);
    setOpen(false);
    onPick(name);
  }

  return (
    <div className="relative max-w-2xl">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && query.trim()) pick(query.trim());
          }}
          placeholder="Search a species, e.g. Rana temporaria"
          aria-label="Search a species"
          className="w-full rounded-md border border-hairline px-4 py-2.5 text-sm text-ink outline-none focus:border-secondary"
        />
        <Button onClick={() => query.trim() && pick(query.trim())}>
          Check
        </Button>
      </div>

      {open && suggestions.length > 0 ? (
        <ul
          role="listbox"
          className="absolute z-10 mt-1 w-full overflow-hidden rounded-md border border-hairline bg-white shadow-sm"
        >
          {suggestions.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                onClick={() => pick(item.name)}
                className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm hover:bg-panel"
              >
                <span className="italic text-ink">{item.name}</span>
                {item.rank ? (
                  <span className="text-xs text-muted">
                    {item.rank.toLowerCase()}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
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

function SummaryView({ report }: { report: SpeciesScoreReport }) {
  const { summary } = report;
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
          No suspicious records found for this species in the sample checked.
        </p>
      )}
    </div>
  );
}

function RecordTable({
  records,
  selectedKey,
  onSelect,
}: {
  records: { key: string; record: CleanRecord }[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-hairline">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-hairline text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-3 py-2 font-bold">ID</th>
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

function Results({ report }: { report: SpeciesScoreReport }) {
  const [minScore, setMinScore] = useState(0.5);
  const [activeReasons, setActiveReasons] = useState<Set<string>>(new Set());
  const [view, setView] = useState<View>("table");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const keyed = useMemo(
    () =>
      report.records.map((record, index) => ({
        key: recordKey(record, index),
        record,
      })),
    [report.records],
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
            record.reasons.some((code) => activeReasons.has(code))),
      ),
    [keyed, minScore, activeReasons],
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

  return (
    <div className="mt-8 flex flex-col gap-6 md:flex-row">
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
        }}
      />

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted">
            <span className="font-bold text-ink">{report.taxon}</span> —{" "}
            {filtered.length} shown
            {report.records_truncated ? " (sample)" : ""}
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

        <div className="mt-3">
          {view === "summary" ? (
            <SummaryView report={report} />
          ) : filtered.length === 0 ? (
            <EmptyState
              title="Nothing matches these filters"
              hint="Lower the minimum suspicion or clear the reason filters."
            />
          ) : view === "map" ? (
            <RecordsMap
              points={points}
              selectedKey={selectedKey}
              onSelect={setSelectedKey}
            />
          ) : (
            <RecordTable
              records={filtered}
              selectedKey={selectedKey}
              onSelect={setSelectedKey}
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

export default function ExplorePage() {
  const [taxon, setTaxon] = useState<string | null>(null);
  const score = useSpeciesScore(taxon);

  // Pick up a species passed from the landing-page search (/explore?taxon=...).
  // Read from the URL directly so the page needs no Suspense boundary. This runs
  // once on the client only, so server and client both first render the empty
  // state and there is no hydration mismatch.
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("taxon");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time read of a browser-only URL param on mount
    if (fromUrl) setTaxon(fromUrl);
  }, []);

  return (
    <div className="min-h-screen bg-white text-ink">
      <header className="border-b border-hairline">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Logo />
          <ul className="hidden items-center gap-8 md:flex">
            {NAV.map((item) => (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className="text-sm font-bold text-ink hover:text-primary"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <a
            href="https://github.com/this-is-rachit/taxonguard"
            className="rounded-md border border-hairline px-5 py-2 text-sm font-bold text-ink hover:border-primary hover:text-primary"
          >
            View on GitHub
          </a>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section className="pt-12">
          <h1 className="text-3xl font-semibold tracking-tight text-ink">
            Explore suspicious records
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted">
            Search any species. TaxonGuard fetches its records, learns where it
            plausibly occurs, and flags the ones that do not fit, with a plain
            reason and a score for each. Filter by reason or score, and view the
            results on a map, in a table, or as a summary.
          </p>
          <div className="mt-6">
            <SearchBar onPick={setTaxon} />
          </div>
          {!taxon ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted">Try:</span>
              {EXAMPLES.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => setTaxon(name)}
                  className="rounded-full bg-panel px-3 py-1 text-xs font-bold italic text-muted hover:text-ink"
                >
                  {name}
                </button>
              ))}
            </div>
          ) : null}
        </section>

        {taxon ? (
          score.isLoading ? (
            <div className="mt-10">
              <LoadingState label={`Fetching and scoring ${taxon}`} />
              <p className="mt-2 text-xs text-muted">
                The first check for a species runs the engine and can take a few
                seconds.
              </p>
            </div>
          ) : score.isError || !score.data ? (
            <div className="mt-10">
              <ErrorState
                title="Could not score this species"
                hint={
                  score.error instanceof Error
                    ? score.error.message
                    : "Try another species, or check that the API is running."
                }
                onRetry={() => score.refetch()}
              />
            </div>
          ) : (
            <Results report={score.data} />
          )
        ) : null}
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-6 text-sm text-muted">
          Open source under the MIT license. An entry for the GBIF Ebbe Nielsen
          Challenge.
        </div>
      </footer>
    </div>
  );
}
