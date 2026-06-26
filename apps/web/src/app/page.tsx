import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { WelcomeTour } from "@/components/tour/WelcomeTour";

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

const HOW_TO = [
  {
    k: "Explore",
    href: "/explore",
    v: "Search any species. TaxonGuard fetches its records, flags the ones that do not fit, and lets you write a correction back to GBIF.",
  },
  {
    k: "Review",
    href: "/review",
    v: "Work through groups of flagged records, confirm the ones that are errors, and track what has been written back to GBIF.",
  },
  {
    k: "Clean my data",
    href: "/clean",
    v: "Upload a file of occurrence records and check it with the same engine. The result stays with you and is never published to GBIF.",
  },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-white text-ink">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6">
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

          <form
            action="/explore"
            method="get"
            className="mt-8 max-w-2xl"
            data-tour="search"
          >
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

          <div
            className="mt-4 flex flex-wrap items-center gap-2"
            data-tour="demos"
          >
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

        <section className="my-16">
          <div className="rounded-lg bg-panel p-10" data-tour="how-it-works">
            <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
              How it works
            </h2>
            <div className="mt-4 grid gap-6 sm:grid-cols-3">
              {STEPS.map((c) => (
                <div key={c.k}>
                  <p className="text-sm font-bold text-ink">{c.k}</p>
                  <p className="mt-2 text-sm leading-6 text-muted">{c.v}</p>
                </div>
              ))}
            </div>
            <p className="mt-8 text-sm leading-6 text-muted">
              Because anyone can contribute to GBIF, it holds records that
              cannot be right. The standard example is a frog recorded in the
              open ocean. TaxonGuard finds these records, explains them, and
              lets an expert send a fix back into GBIF.{" "}
              <a
                href="/about"
                className="font-bold text-primary hover:underline"
              >
                Read more about how it works
              </a>
              .
            </p>
          </div>

          <div className="mt-10" data-tour="how-to">
            <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
              How to use this site
            </h2>
            <div className="mt-4 grid gap-6 sm:grid-cols-3">
              {HOW_TO.map((c) => (
                <a
                  key={c.k}
                  href={c.href}
                  className="block rounded-lg border border-hairline p-6 hover:border-primary"
                >
                  <p className="text-sm font-bold text-ink">{c.k}</p>
                  <p className="mt-2 text-sm leading-6 text-muted">{c.v}</p>
                  <p className="mt-3 text-sm font-bold text-primary">Open →</p>
                </a>
              ))}
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />

      <WelcomeTour />
    </div>
  );
}
