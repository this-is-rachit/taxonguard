// Small presentational components for the three data states. Following the
// design copy guidance: errors explain what to do, and an empty screen invites
// action rather than apologizing.

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div
      className="flex items-center gap-2 p-sm text-sm text-muted"
      role="status"
    >
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-hairline border-t-secondary"
        aria-hidden="true"
      />
      {label}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-hairline p-md text-center">
      <p className="text-sm font-bold text-ink">{title}</p>
      {hint ? <p className="mt-2 text-sm text-muted">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({
  title = "Could not reach the API",
  hint = "Start the API and try again.",
  onRetry,
}: {
  title?: string;
  hint?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="rounded-lg border border-error/40 bg-error/5 p-md"
      role="alert"
    >
      <p className="text-sm font-bold text-error">{title}</p>
      <p className="mt-2 text-sm text-muted">{hint}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-sm font-bold text-primary hover:underline"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
