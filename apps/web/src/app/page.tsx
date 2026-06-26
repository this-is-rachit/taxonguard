import { SiteHeader } from "@/components/SiteHeader";

const EXAMPLES = ["Rana temporaria", "Vulpes lagopus", "Panthera leo"];

const STEPS = [
  {
    k: "Detect",
    v: "A niche and outlier model learns each species from its own records and scores every record for plausibility.",
  },
  {
    k: "Explain",
    v: "Each flag gets one plain sentence a human can judge at a glance, never a black-box verdict.",
  },
  {
    k: "Write back",
    v: "A confirmed rule is published to GBIF and keeps cleaning future data for everyone.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-ink">
      <SiteHeader />

      <main className="mx-auto max-w-6xl px-6">
        <section className="pt-16">
          <p className="text-sm font-bold uppercase tracking-wide text-primary">
            GBIF Ebbe Nielsen Challenge
          </p>
          <h1 className="mt-4 text-5xl font-semibold leading-none tracking-tight text-ink">
            TaxonGuard
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
            A spell-checker for the world&apos;s species records. Search any
            species and TaxonGuard finds the sightings that cannot be right,
            explains why, and lets an expert confirm a fix that flows back into
            GBIF.
          </p>

          <form action="/explore" method="get" className="mt-8 max-w-2xl">
            <div className="flex gap-2">
              <input
                type="text"
                name="taxon"
                placeholder="Search a species, e.g. Rana temporaria"
                aria-label="Search a species"
                className="w-full rounded-md border border-hairline px-4 py-2.5 text-sm text-ink outline-none focus:border-secondary"
              />
              <button
                type="submit"
                className="shrink-0 rounded-md bg-secondary px-5 py-2.5 text-sm font-bold text-white hover:opacity-90"
              >
                Explore
              </button>
            </div>
          </form>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted">Try:</span>
            {EXAMPLES.map((name) => (
              <a
                key={name}
                href={`/explore?taxon=${encodeURIComponent(name)}`}
                className="rounded-full bg-panel px-3 py-1 text-xs font-bold italic text-muted hover:text-ink"
              >
                {name}
              </a>
            ))}
            <span className="text-xs text-muted">or</span>
            <a
              href="/clean"
              className="text-xs font-bold text-primary hover:underline"
            >
              clean your own file
            </a>
          </div>
        </section>

        <section className="my-16 rounded-lg bg-panel p-10">
          <div className="grid gap-6 sm:grid-cols-3">
            {STEPS.map((c) => (
              <div key={c.k}>
                <p className="text-sm font-bold text-ink">{c.k}</p>
                <p className="mt-2 text-sm leading-6 text-muted">{c.v}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm text-muted">
            Open the Explore screen to search a species and see its suspicious
            records on a map, in a table, or as a summary. The review screen
            adds the expert confirm step and writes a confirmed rule back to
            GBIF.
          </p>
        </section>
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
