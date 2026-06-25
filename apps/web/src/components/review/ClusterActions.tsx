"use client";

import { useState } from "react";

import { type DecisionState } from "@/lib/api";
import { useDecision } from "@/lib/queries";
import { Button } from "@/components/ui/Button";

// Confirm, reject, or refine a cluster's draft rule. The decision is recorded by
// the API, which writes a confirmed rule back to GBIF when credentials are set;
// the status makes the "written to GBIF" or "recorded, not yet written" state
// explicit.
export function ClusterActions({
  clusterId,
  decision,
}: {
  clusterId: string;
  decision: DecisionState | null;
}) {
  const [note, setNote] = useState("");
  const mutation = useDecision(clusterId);

  function decide(action: "confirm" | "reject" | "refine") {
    mutation.mutate({ action, note: note.trim() || null });
  }

  return (
    <div className="mt-6">
      <p className="text-xs font-bold uppercase tracking-wide text-muted">
        Decision
      </p>

      <label htmlFor="decision-note" className="sr-only">
        Optional note for this decision
      </label>
      <textarea
        id="decision-note"
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder="Optional note, for example why this is or is not an error"
        rows={2}
        className="mt-2 w-full rounded-md border border-hairline p-2 text-sm text-ink placeholder:text-tertiary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary"
      />

      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={() => decide("confirm")} disabled={mutation.isPending}>
          Confirm
        </Button>
        <Button
          variant="secondary"
          onClick={() => decide("reject")}
          disabled={mutation.isPending}
        >
          Reject
        </Button>
        <Button
          variant="secondary"
          onClick={() => decide("refine")}
          disabled={mutation.isPending}
        >
          Refine
        </Button>
      </div>

      <div aria-live="polite" className="mt-3 text-sm">
        {mutation.isError ? (
          <span className="text-error">
            Could not record the decision. Try again.
          </span>
        ) : null}
        {decision ? (
          decision.written_to_gbif ? (
            <span className="text-muted">
              Recorded:{" "}
              <span className="font-bold text-ink">{decision.action}</span>
              {decision.value ? ` (${decision.value})` : ""}. Written to GBIF
              {decision.annotation_url ? (
                <>
                  {" "}
                  <a
                    href={decision.annotation_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-bold text-primary hover:underline"
                  >
                    View the annotation
                  </a>
                </>
              ) : null}
              .
            </span>
          ) : (
            <div className="text-muted">
              <span>
                Recorded:{" "}
                <span className="font-bold text-ink">{decision.action}</span>
                {decision.value ? ` (${decision.value})` : ""}. Not yet written
                to GBIF.
              </span>
              {decision.manual_instructions ? (
                <details className="mt-2">
                  <summary className="cursor-pointer font-bold text-ink">
                    Create this rule manually
                  </summary>
                  <pre className="mt-2 whitespace-pre-wrap break-all rounded-md border border-hairline bg-panel p-2 font-mono text-xs text-ink">
                    {decision.manual_instructions}
                  </pre>
                </details>
              ) : null}
            </div>
          )
        ) : null}
      </div>
    </div>
  );
}
