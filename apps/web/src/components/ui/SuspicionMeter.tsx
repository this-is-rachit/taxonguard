// A compact bar for a 0..1 suspicion score. The fill widens and shifts from the
// brand green toward the error red as the score rises, so severity reads at a
// glance. The value is also shown as text for accessibility.
export function SuspicionMeter({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(1, score));
  const percent = Math.round(clamped * 100);
  const color =
    clamped >= 0.8
      ? "bg-error"
      : clamped >= 0.5
        ? "bg-secondary"
        : "bg-primary";

  return (
    <div className="flex items-center gap-2">
      <div
        className="h-1.5 w-24 overflow-hidden rounded-full bg-hairline"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Suspicion score"
      >
        <div className={`h-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="text-xs font-bold tabular-nums text-muted">
        {clamped.toFixed(2)}
      </span>
    </div>
  );
}
