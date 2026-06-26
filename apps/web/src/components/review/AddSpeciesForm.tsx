"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { HelpTip } from "@/components/ui/HelpTip";
import { useAddReviewTaxon } from "@/lib/queries";

type Realm = "terrestrial" | "freshwater" | "marine";

// A small form that adds a species to the Review set. The realm is required
// because the land or sea check needs to know where the species belongs, and that
// cannot be inferred from the name. On success the clusters list is refetched, so
// the new species appears in the list and on the map.
export function AddSpeciesForm() {
  const [name, setName] = useState("");
  const [realm, setRealm] = useState<Realm>("terrestrial");
  const mutation = useAddReviewTaxon();
  const trimmed = name.trim();

  const added = mutation.isSuccess ? mutation.data : null;
  const successText = added
    ? `Added ${added.taxon}: ${added.cluster_count} ` +
      `${added.cluster_count === 1 ? "cluster" : "clusters"} from ` +
      `${added.flagged_records} flagged ` +
      `${added.flagged_records === 1 ? "record" : "records"}.`
    : null;

  function submit() {
    if (!trimmed || mutation.isPending) return;
    mutation.mutate({ name: trimmed, realm }, { onSuccess: () => setName("") });
  }

  return (
    <div className="mt-md rounded-lg border border-hairline bg-white p-sm">
      <span className="inline-flex items-center gap-1">
        <p className="text-xs font-bold uppercase tracking-wide text-muted">
          Add a species
        </p>
        <HelpTip
          label="About adding a species"
          text="Fetch any species from GBIF and check it for suspicious records. Pick its habitat so the land or sea check knows where it belongs. The first add runs the engine and can take a few seconds."
        />
      </span>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submit();
          }}
          placeholder="Scientific name, for example Bufo bufo"
          aria-label="Scientific name to add to review"
          disabled={mutation.isPending}
          className="w-full rounded-md border border-hairline px-3 py-2 text-sm text-ink outline-none focus:border-secondary disabled:opacity-50 sm:w-72"
        />
        <select
          value={realm}
          onChange={(event) => setRealm(event.target.value as Realm)}
          aria-label="Habitat realm"
          disabled={mutation.isPending}
          className="rounded-md border border-hairline px-3 py-2 text-sm text-ink outline-none focus:border-secondary disabled:opacity-50"
        >
          <option value="terrestrial">Lives on land</option>
          <option value="freshwater">Lives in fresh water</option>
          <option value="marine">Lives in the sea</option>
        </select>
        <Button onClick={submit} disabled={!trimmed || mutation.isPending}>
          {mutation.isPending ? "Adding…" : "Add to review"}
        </Button>
      </div>

      {mutation.isPending ? (
        <p className="mt-3 text-sm text-muted" role="status">
          Fetching and scoring {trimmed}. This can take a few seconds.
        </p>
      ) : null}

      {mutation.isError ? (
        <p className="mt-3 text-sm text-error" role="alert">
          {mutation.error.message}
        </p>
      ) : null}

      {successText ? (
        <p className="mt-3 text-sm text-primary" role="status">
          {successText}
        </p>
      ) : null}
    </div>
  );
}
