"use client";

import { useEffect, useState } from "react";

import { SiteHeader } from "@/components/SiteHeader";
import { RecordsExplorer } from "@/components/explore/RecordsExplorer";
import { Button } from "@/components/ui/Button";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useSpeciesScore, useSpeciesSuggest } from "@/lib/queries";

const EXAMPLES = [
  "Rana temporaria",
  "Vulpes lagopus",
  "Panthera leo",
  "Bradypus variegatus",
];

function SearchBar({ onPick }: { onPick: (name: string) => void }) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(timer);
  }, [query]);

  const suggest = useSpeciesSuggest(debounced);
  const suggestions = suggest.data ?? [];

  function pick(name: string) {
    setQuery(name);
    setOpen(false);
    onPick(name);
  }

  return (
    <div className="relative max-w-2xl">
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && query.trim()) pick(query.trim());
          }}
          placeholder="Search a species, e.g. Rana temporaria"
          aria-label="Search a species"
          className="w-full rounded-md border border-hairline px-4 py-2.5 text-sm text-ink outline-none focus:border-secondary"
        />
        <Button onClick={() => query.trim() && pick(query.trim())}>
          Check
        </Button>
      </div>

      {open && suggestions.length > 0 ? (
        <ul
          role="listbox"
          className="absolute z-10 mt-1 w-full overflow-hidden rounded-md border border-hairline bg-white shadow-sm"
        >
          {suggestions.map((item) => (
            <li key={item.key}>
              <button
                type="button"
                onClick={() => pick(item.name)}
                className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm hover:bg-panel"
              >
                <span className="italic text-ink">{item.name}</span>
                {item.rank ? (
                  <span className="text-xs text-muted">
                    {item.rank.toLowerCase()}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default function ExplorePage() {
  const [taxon, setTaxon] = useState<string | null>(null);
  const score = useSpeciesScore(taxon);

  // Pick up a species passed from the landing-page search (/explore?taxon=...).
  // Read from the URL directly so the page needs no Suspense boundary. This runs
  // once on the client only, so server and client both first render the empty
  // state and there is no hydration mismatch.
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("taxon");
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time read of a browser-only URL param on mount
    if (fromUrl) setTaxon(fromUrl);
  }, []);

  return (
    <div className="min-h-screen bg-white text-ink">
      <SiteHeader />

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section className="pt-12">
          <h1 className="text-3xl font-semibold tracking-tight text-ink">
            Explore suspicious records
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted">
            Search any species. TaxonGuard fetches its records, learns where it
            plausibly occurs, and flags the ones that do not fit, with a plain
            reason and a score for each. Filter by reason, score, or a drawn
            area, and view the results on a map, in a table, or as a summary.
          </p>
          <div className="mt-6">
            <SearchBar onPick={setTaxon} />
          </div>
          {!taxon ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted">Try:</span>
              {EXAMPLES.map((name) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => setTaxon(name)}
                  className="rounded-full bg-panel px-3 py-1 text-xs font-bold italic text-muted hover:text-ink"
                >
                  {name}
                </button>
              ))}
            </div>
          ) : null}
        </section>

        {taxon ? (
          score.isLoading ? (
            <div className="mt-10">
              <LoadingState label={`Fetching and scoring ${taxon}`} />
              <p className="mt-2 text-xs text-muted">
                The first check for a species runs the engine and can take a few
                seconds.
              </p>
            </div>
          ) : score.isError || !score.data ? (
            <div className="mt-10">
              <ErrorState
                title="Could not score this species"
                hint={
                  score.error instanceof Error
                    ? score.error.message
                    : "Try another species, or check that the API is running."
                }
                onRetry={() => score.refetch()}
              />
            </div>
          ) : (
            <RecordsExplorer
              records={score.data.records}
              summary={score.data.summary}
              taxonLabel={score.data.taxon}
              truncated={score.data.records_truncated}
              annotateTaxon={score.data.taxon}
            />
          )
        ) : null}
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-6 text-sm text-muted">
          Open source under the MIT license. An entry for the GBIF Ebbe Nielsen
          Challenge.
        </div>
      </footer>
    </div>
  );
}
