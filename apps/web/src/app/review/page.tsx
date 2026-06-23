"use client";

import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/Logo";
import { ClusterListItem } from "@/components/review/ClusterListItem";
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

      <div className="mt-6 rounded-lg border border-dashed border-hairline p-md text-center text-sm text-muted">
        The map and the confirm, reject, and refine actions arrive next.
      </div>
    </div>
  );
}

export default function ReviewPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: clusters, isLoading, isError, refetch } = useClusters();

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
          Each cluster groups nearby flagged records of one taxon. Pick one to
          see its records and the draft rule it would write back to GBIF.
        </p>

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
                onSelect={() => setSelectedId(cluster.cluster_id)}
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
