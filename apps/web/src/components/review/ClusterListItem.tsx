import { type ClusterSummary } from "@/lib/api";
import { reasonLabel } from "@/lib/reasons";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { SuspicionMeter } from "@/components/ui/SuspicionMeter";

// One flagged cluster in the list. Shows the taxon, the worst suspicion score,
// the record count, the reasons present, and the one-sentence explanation.
export function ClusterListItem({
  cluster,
  selected,
  onSelect,
}: {
  cluster: ClusterSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const reasons = Object.keys(cluster.reason_counts);

  return (
    <Card selected={selected} className="cursor-pointer hover:border-primary">
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        aria-label={`Select ${cluster.taxon} cluster`}
        className="block w-full text-left focus-visible:outline-none"
      >
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-bold italic text-ink">{cluster.taxon}</p>
          <SuspicionMeter score={cluster.max_score} />
        </div>
        <p className="mt-1 text-xs text-muted">
          {cluster.count} flagged {cluster.count === 1 ? "record" : "records"}
        </p>
        <p className="mt-2 text-sm leading-6 text-muted">
          {cluster.explanation}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {reasons.map((code) => (
            <Badge key={code}>{reasonLabel(code)}</Badge>
          ))}
          {cluster.decision ? (
            <Badge
              tone={cluster.decision.action === "reject" ? "error" : "primary"}
            >
              {cluster.decision.action}
            </Badge>
          ) : null}
        </div>
      </button>
    </Card>
  );
}
