"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { Logo } from "@/components/Logo";
import { ClusterActions } from "@/components/review/ClusterActions";
import { ClusterListItem } from "@/components/review/ClusterListItem";
import { ClusterMap } from "@/components/review/ClusterMap";
import { Badge } from "@/components/ui/Badge";
import { SuspicionMeter } from "@/components/ui/SuspicionMeter";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { reasonLabel } from "@/lib/reasons";
import { useCluster, useClusters } from "@/lib/queries";

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
  const { data: clusters, isLoading, isError, refetch } = useClusters();
  const handleSelect = useCallback((id: string) => setSelectedId(id), []);

  return (
    <div className="min-h-screen bg-white text-ink">
      <header className="border-b border-hairline">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Logo />
          <Link
            href="/"
            className="text-sm font-bold text-ink hover:text-primary"
          >
            Home
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-md">
        <h1 className="text-3xl font-semibold tracking-tight text-ink">
          Review flagged clusters
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Each cluster groups nearby flagged records of one taxon. Pick one on
          the map or in the list to see its records and the draft rule it would
          write back to GBIF.
        </p>

        <div className="mt-md">
          <ClusterMap
            clusters={clusters ?? []}
            selectedId={selectedId}
            onSelect={handleSelect}
          />
        </div>

        <div className="mt-md grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <section
            aria-label="Flagged clusters"
            className="flex flex-col gap-3"
          >
            {isLoading ? <LoadingState label="Loading clusters" /> : null}
            {isError ? <ErrorState onRetry={() => refetch()} /> : null}
            {clusters && clusters.length === 0 ? (
              <EmptyState
                title="No flagged clusters"
                hint="Build a taxon cache and start the API to see results here."
              />
            ) : null}
            {clusters?.map((cluster) => (
              <ClusterListItem
                key={cluster.cluster_id}
                cluster={cluster}
                selected={cluster.cluster_id === selectedId}
                onSelect={() => handleSelect(cluster.cluster_id)}
              />
            ))}
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
    </div>
  );
}
