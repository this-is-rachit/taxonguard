// Shows the outcome of writing a rule back to GBIF, in one consistent place.
// Shared by the Explore "propose a rule" action and the Review decision panel, so
// both screens describe the result the same way. The copy explains the
// no-credentials case, so a reviewer without a GBIF account understands why a rule
// was not published rather than seeing a silent failure.

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
      <div className="text-muted">
        Written to GBIF.
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
      </div>
    );
  }

  return (
    <div className="text-muted">
      <span>
        Not yet written to GBIF
        {manualInstructions
          ? ", because no GBIF credentials are configured."
          : detail
            ? `. ${detail}`
            : "."}
      </span>
      {manualInstructions ? (
        <details className="mt-2">
          <summary className="cursor-pointer font-bold text-ink">
            Create this rule manually
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-all rounded-md border border-hairline bg-panel p-2 font-mono text-xs text-ink">
            {manualInstructions}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
