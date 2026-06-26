"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { type MapPoint, RecordsMap } from "@/components/explore/RecordsMap";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { AddSpeciesForm } from "@/components/review/AddSpeciesForm";
import { ClusterActions } from "@/components/review/ClusterActions";
import { ClusterListItem } from "@/components/review/ClusterListItem";
import { Badge } from "@/components/ui/Badge";
import { HelpTip } from "@/components/ui/HelpTip";
import { SuspicionMeter } from "@/components/ui/SuspicionMeter";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { reasonLabel } from "@/lib/reasons";
import { useCluster, useClusters } from "@/lib/queries";

const REASON_ORDER = [
  "realm_mismatch",
  "zero_coordinates",
  "equal_coordinates",
  "gridded_coordinates",
  "institution_coordinates",
  "environmental_outlier",
];

type ReviewStatus = "all" | "undecided" | "confirm" | "reject" | "refine";

// Show the cluster list in pages so a long list does not push the page down.
const PAGE_SIZE = 20;

function ClusterDetailPanel({ clusterId }: { clusterId: string }) {
  const { data, isLoading, isError, refetch } = useCluster(clusterId);

  if (isLoading) return <LoadingState label="Loading cluster" />;
  if (isError || !data) return <ErrorState onRetry={() => refetch()} />;

  return (
    <div>
      <p className="text-sm font-bold italic text-ink">{data.taxon}</p>
      <div className="mt-2">
        <SuspicionMeter score={data.max_score} />
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">{data.explanation}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        {Object.entries(data.reason_counts).map(([code, n]) => (
          <Badge key={code}>
            {reasonLabel(code)} ({n})
          </Badge>
        ))}
      </div>

      <div className="mt-6 rounded-lg border border-hairline bg-panel p-sm">
        <p className="text-xs font-bold uppercase tracking-wide text-muted">
          Draft rule
        </p>
        <p className="mt-2 text-sm text-ink">
          {data.rule.record_count}{" "}
          {data.rule.record_count === 1 ? "record" : "records"} marked{" "}
          <span className="font-bold">{data.rule.value}</span>
        </p>
        <p className="mt-1 break-all font-mono text-xs text-muted">
          {data.rule.geometry}
        </p>
      </div>

      <div className="mt-6">
        <p className="text-xs font-bold uppercase tracking-wide text-muted">
          Records
        </p>
        <ul role="list" className="mt-2 flex flex-col gap-2">
          {data.records.map((record, index) => (
            <li
              key={record.gbif_id ?? index}
              className="flex items-center justify-between gap-3 rounded-md border border-hairline p-2"
            >
              <div className="min-w-0">
                <p className="text-xs font-bold text-ink">
                  {record.gbif_id ? `GBIF ${record.gbif_id}` : "Record"}
                </p>
                <p className="truncate text-xs text-muted">
                  {record.latitude.toFixed(3)}, {record.longitude.toFixed(3)}
                  {" — "}
                  {record.reasons.map(reasonLabel).join(", ")}
                </p>
              </div>
              <SuspicionMeter score={record.suspicion_score} />
            </li>
          ))}
        </ul>
      </div>

      <ClusterActions clusterId={data.cluster_id} decision={data.decision} />
    </div>
  );
}

export default function ReviewPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [activeReasons, setActiveReasons] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState<ReviewStatus>("all");
  const [page, setPage] = useState(1);
  const { data: clusters, isLoading, isError, refetch } = useClusters();
  const handleSelect = useCallback((id: string) => setSelectedId(id), []);

  // Return to the first page whenever the filters change, so the visible page
  // always reflects the current filter rather than a stale page number. This is
  // done during render (the React pattern for adjusting state on a changed input)
  // rather than in an effect, to avoid an extra render pass.
  const filterKey = `${query}|${[...activeReasons].sort().join(",")}|${status}`;
  const [seenFilterKey, setSeenFilterKey] = useState(filterKey);
  if (filterKey !== seenFilterKey) {
    setSeenFilterKey(filterKey);
    setPage(1);
  }

  const all = useMemo(() => clusters ?? [], [clusters]);

  const presentReasons = useMemo(() => {
    const set = new Set<string>();
    for (const cluster of all) {
      for (const code of Object.keys(cluster.reason_counts)) set.add(code);
    }
    return REASON_ORDER.filter((code) => set.has(code));
  }, [all]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return all.filter((cluster) => {
      if (q && !cluster.taxon.toLowerCase().includes(q)) return false;
      if (
        activeReasons.size > 0 &&
        !Object.keys(cluster.reason_counts).some((code) =>
          activeReasons.has(code),
        )
      ) {
        return false;
      }
      if (status === "undecided" && cluster.decision) return false;
      if (
        status !== "all" &&
        status !== "undecided" &&
        cluster.decision?.action !== status
      ) {
        return false;
      }
      return true;
    });
  }, [all, query, activeReasons, status]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const paged = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  const points: MapPoint[] = useMemo(
    () =>
      filtered.map((cluster) => ({
        key: cluster.cluster_id,
        latitude: cluster.latitude,
        longitude: cluster.longitude,
        score: cluster.max_score,
        label: `${cluster.taxon} (${cluster.max_score.toFixed(2)})`,
      })),
    [filtered],
  );

  function toggleReason(code: string) {
    setActiveReasons((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  const hasFilters =
    query.trim() !== "" || activeReasons.size > 0 || status !== "all";

  return (
    <div className="flex min-h-screen flex-col bg-white text-ink">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-md">
        <h1 className="text-3xl font-semibold tracking-tight text-ink">
          Review flagged clusters
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Each cluster groups nearby flagged records of one taxon. Pick one on
          the map or in the list to see its records and the draft rule it would
          write back to GBIF. Looking for a species that is not listed here?{" "}
          <Link
            href="/explore"
            className="font-bold text-primary hover:underline"
          >
            Search any species in Explore
          </Link>
          .
        </p>

        <AddSpeciesForm />

        <div className="mt-md rounded-lg border border-hairline bg-white p-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <p className="text-xs font-bold uppercase tracking-wide text-muted">
                Filter clusters
              </p>
              <HelpTip
                label="About the cluster filters"
                text="Narrow the list by species name, by the reasons a cluster was flagged for, or by whether you have already decided on it. The map and the list both update."
              />
            </span>
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter by species name"
              aria-label="Filter clusters by species"
              className="w-full rounded-md border border-hairline px-3 py-2 text-sm text-ink outline-none focus:border-secondary sm:w-64"
            />
            <label htmlFor="review-status" className="sr-only">
              Filter by decision status
            </label>
            <select
              id="review-status"
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as ReviewStatus)
              }
              className="rounded-md border border-hairline px-3 py-2 text-sm text-ink outline-none focus:border-secondary"
            >
              <option value="all">All decisions</option>
              <option value="undecided">Undecided</option>
              <option value="confirm">Confirmed</option>
              <option value="reject">Rejected</option>
              <option value="refine">Refined</option>
            </select>
            <span className="text-xs text-muted">
              {filtered.length} of {all.length} cluster
              {all.length === 1 ? "" : "s"}
            </span>
            {hasFilters ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setActiveReasons(new Set());
                  setStatus("all");
                }}
                className="text-xs font-bold text-primary hover:underline"
              >
                Reset
              </button>
            ) : null}
          </div>

          {presentReasons.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {presentReasons.map((code) => {
                const active = activeReasons.has(code);
                return (
                  <button
                    key={code}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleReason(code)}
                    className={`rounded-md border px-2.5 py-1 text-xs font-bold ${
                      active
                        ? "border-secondary bg-secondary/5 text-ink"
                        : "border-hairline text-muted hover:border-primary"
                    }`}
                  >
                    {reasonLabel(code)}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="mt-md">
          <RecordsMap
            points={points}
            selectedKey={selectedId}
            onSelect={handleSelect}
            ariaLabel="Map of flagged clusters"
          />
        </div>

        <div className="mt-md grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <section
            aria-label="Flagged clusters"
            className="flex flex-col gap-3"
          >
            {isLoading ? <LoadingState label="Loading clusters" /> : null}
            {isError ? <ErrorState onRetry={() => refetch()} /> : null}
            {clusters && all.length === 0 ? (
              <EmptyState
                title="No flagged clusters"
                hint="Build a taxon cache and start the API to see results here."
              />
            ) : null}
            {clusters && all.length > 0 && filtered.length === 0 ? (
              <EmptyState
                title="No clusters match these filters"
                hint="Clear the species filter, the reason filters, or the decision status."
              />
            ) : null}
            {paged.map((cluster) => (
              <ClusterListItem
                key={cluster.cluster_id}
                cluster={cluster}
                selected={cluster.cluster_id === selectedId}
                onSelect={() => handleSelect(cluster.cluster_id)}
              />
            ))}

            {filtered.length > PAGE_SIZE ? (
              <div className="mt-1 flex items-center justify-between gap-3 border-t border-hairline pt-3">
                <span className="text-xs text-muted">
                  Showing {(currentPage - 1) * PAGE_SIZE + 1}–
                  {Math.min(currentPage * PAGE_SIZE, filtered.length)} of{" "}
                  {filtered.length}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage <= 1}
                    className="rounded-md border border-hairline px-2.5 py-1 text-xs font-bold text-ink hover:border-primary disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="text-xs text-muted">
                    Page {currentPage} of {pageCount}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setPage(Math.min(pageCount, currentPage + 1))
                    }
                    disabled={currentPage >= pageCount}
                    className="rounded-md border border-hairline px-2.5 py-1 text-xs font-bold text-ink hover:border-primary disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            ) : null}
          </section>

          <section
            aria-label="Cluster detail"
            className="rounded-lg border border-hairline bg-white p-md"
          >
            {selectedId ? (
              <ClusterDetailPanel clusterId={selectedId} />
            ) : (
              <EmptyState
                title="Select a cluster"
                hint="Pick a cluster on the left to see its records and draft rule."
              />
            )}
          </section>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
