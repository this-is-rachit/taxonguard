// Shows the outcome of writing a rule back to GBIF, in one consistent place.
// Used by the Explore "propose a rule" action; the Review screen will share it
// too. The copy is plain and explains the no-credentials case, so a reviewer
// without a GBIF account understands why a rule was not published rather than
// seeing a silent failure.

export function WriteBackResult({
  written,
  annotationUrl,
  manualInstructions,
  detail,
}: {
  written: boolean;
  annotationUrl?: string | null;
  manualInstructions?: string | null;
  detail?: string | null;
}) {
  if (written) {
    return (
      <p className="text-sm text-muted" aria-live="polite">
        Published to GBIF as a suspicious-records rule.
        {annotationUrl ? (
          <>
            {" "}
            <a
              href={annotationUrl}
              target="_blank"
              rel="noreferrer"
              className="font-bold text-primary hover:underline"
            >
              View the annotation
            </a>
          </>
        ) : null}
      </p>
    );
  }

  return (
    <div className="text-sm text-muted" aria-live="polite">
      <p>
        {manualInstructions
          ? "This rule was not published, because no GBIF credentials are configured. You can create it by hand:"
          : (detail ?? "This rule was not published.")}
      </p>
      {manualInstructions ? (
        <details className="mt-2">
          <summary className="cursor-pointer font-bold text-ink">
            Show the rule to create manually
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-all rounded-md border border-hairline bg-panel p-2 font-mono text-xs text-ink">
            {manualInstructions}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
