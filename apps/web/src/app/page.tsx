import { Logo } from "@/components/Logo";

const NAV = [
  { label: "Detect", href: "#" },
  { label: "Review", href: "/review" },
  { label: "Clean my data", href: "#" },
  { label: "About", href: "#" },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-ink">
      <header className="border-b border-hairline">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Logo />
          <ul className="hidden items-center gap-8 md:flex">
            {NAV.map((item) => (
              <li key={item.label}>
                <a
                  href={item.href}
                  className="text-sm font-bold text-ink hover:text-primary"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
          <a
            href="https://github.com/this-is-rachit/taxonguard"
            className="rounded-md border border-hairline px-5 py-2 text-sm font-bold text-ink hover:border-primary hover:text-primary"
          >
            View on GitHub
          </a>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6">
        <section className="pt-16">
          <p className="text-sm font-bold uppercase tracking-wide text-primary">
            GBIF Ebbe Nielsen Challenge
          </p>
          <h1 className="mt-4 text-5xl font-semibold leading-none tracking-tight text-ink">
            TaxonGuard
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
            Detect, explain, expert-confirm, and write back implausible GBIF
            occurrence records. TaxonGuard learns where each taxon plausibly
            occurs from its own records, flags the records that do not fit, and
            lets a domain expert confirm a fix that cleans existing data and
            keeps catching the same error in future data drops.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="/review"
              className="rounded-md bg-secondary px-5 py-2.5 text-sm font-bold text-white hover:opacity-90"
            >
              Open the review screen
            </a>
            <a
              href="#"
              className="rounded-md border border-hairline px-5 py-2.5 text-sm font-bold text-ink hover:border-primary hover:text-primary"
            >
              How it works
            </a>
          </div>
        </section>

        <section className="my-16 rounded-lg bg-panel p-10">
          <div className="grid gap-6 sm:grid-cols-3">
            {[
              {
                k: "Detect",
                v: "A niche and outlier model scores every record for plausibility.",
              },
              {
                k: "Explain",
                v: "Each flag gets one plain sentence a human can judge at a glance.",
              },
              {
                k: "Write back",
                v: "A confirmed rule is published to GBIF and cleans future data.",
              },
            ].map((c) => (
              <div key={c.k}>
                <p className="text-sm font-bold text-ink">{c.k}</p>
                <p className="mt-2 text-sm leading-6 text-muted">{c.v}</p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm text-muted">
            The live review screen is built in Phase 5. This page confirms the
            web app scaffold, the light theme, and the brand palette.
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
