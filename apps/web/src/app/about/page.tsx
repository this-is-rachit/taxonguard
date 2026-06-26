import type { Metadata } from "next";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = {
  title: "About TaxonGuard",
  description:
    "How TaxonGuard finds, explains, and corrects implausible GBIF occurrence records, and how it writes confirmed corrections back to GBIF.",
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-10 max-w-3xl">
      <h2 className="text-xl font-semibold tracking-tight text-ink">{title}</h2>
      <div className="mt-3 space-y-3 text-base leading-7 text-muted">
        {children}
      </div>
    </section>
  );
}

export default function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col bg-white text-ink">
      <SiteHeader />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 pb-20">
        <section className="max-w-3xl pt-12">
          <p className="text-sm font-bold uppercase tracking-wide text-primary">
            About
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight text-ink">
            How TaxonGuard works
          </h1>
          <p className="mt-5 text-base leading-7 text-muted">
            TaxonGuard finds occurrence records in GBIF that are ecologically or
            taxonomically implausible, explains why each one is suspect in a
            single plain sentence, lets a domain expert confirm or reject a
            group of them, and writes the confirmed judgment back to GBIF&apos;s
            occurrence-annotation system. A confirmed rule cleans the existing
            records and continues to catch matching records in future data. It
            is an open-source entry for the GBIF Ebbe Nielsen Challenge.
          </p>
        </section>

        <Section title="The problem">
          <p>
            GBIF is a single shared record of where species have been observed,
            with billions of rows contributed by many sources. Because anyone
            can contribute, the data contains records that cannot be right. The
            standard example is a frog recorded in the open ocean. Range and
            identification errors of this kind are a long-standing,
            still-unsolved data-quality problem, and GBIF has no built-in
            outlier detection: users are left to find these records themselves.
          </p>
        </Section>

        <Section title="What it does, in five steps">
          <p>
            First, it learns where a species plausibly occurs from that
            species&apos; own GBIF records, so an exception defines its own
            normal. Second, it scans the records and flags the implausible ones.
            Third, it explains each flag in one plain sentence. Fourth, it lets
            an expert confirm once, which resolves the whole group and keeps
            catching the same error on future records. Fifth, it writes the
            confirmed rule back to GBIF so every data user benefits.
          </p>
        </Section>

        <Section title="How the detection works">
          <p>
            The component that decides whether a record is suspect is a niche
            and outlier model doing measurable, testable arithmetic, not a
            language model. An isolation forest is fitted on each species&apos;
            own climate conditions, so a record in a climate far outside the
            species&apos; range scores high. Alongside it, fast deterministic
            checks catch a land species recorded in the sea, coordinates at
            exactly zero, latitude equal to longitude, whole-degree grid
            centroids, and coordinates that sit on a known institution. The
            signals are combined into one suspicion score with a per-signal
            reason breakdown.
          </p>
          <p>
            A language model, when configured, only writes the explanation
            sentence, and it is held to a strict rule: it may not introduce any
            number that is not in the computed evidence, and any sentence that
            does is rejected in favour of a deterministic one. Remove the
            language model and the tool still works; you read the numbers
            instead of a sentence. This is a data-quality engine with a thin,
            optional language layer for readability, not a language model with a
            thin wrapper.
          </p>
        </Section>

        <Section title="Why it is safe to trust">
          <p>
            TaxonGuard flags records as suspicious; it never calls them wrong
            and never deletes anything. A human confirms before any write-back,
            so the expert is the safety net. Outlier flags are down-weighted
            where sampling is sparse, so an under-recorded area is not treated
            as an error. Every flag shows its reasons, so a weak flag is easy to
            ignore. And the whole engine is measurable: it is run against
            records with known errors and scored on how many it catches against
            how many false alarms it raises.
          </p>
        </Section>

        <Section title="How accurate it is">
          <p>
            Accuracy is reported on a real, citable GBIF download rather than
            only on synthetic data. Known errors of each type are planted into a
            real occurrence set for the common frog (Rana temporaria) in Great
            Britain, recorded under DOI 10.15468/dl.bpfzpj, and the engine is
            measured on a held-out split that was not used to tune it. The
            deterministic checks reach full recall with a near-zero
            false-positive rate. Climate outliers are the honest exception: real
            climate niches are messier and multi-modal, so the mildest climate
            errors sit below the operating threshold. The evaluation reports
            both the favourable synthetic numbers and the lower, more honest
            real-data numbers, and the gap between them is the point.
          </p>
        </Section>

        <Section title="How GBIF data is used and returned">
          <p>
            TaxonGuard reads occurrence records and scientific names through
            GBIF&apos;s public APIs, and enriches them with open climate data
            (WorldClim) and open land and sea boundaries (Natural Earth). When
            an expert confirms a rule, it is written back to GBIF&apos;s
            experimental occurrence-annotation system as a taxon, a polygon, and
            a controlled value of &quot;suspicious&quot;. Returning a new
            capability to the GBIF network, with corrections flowing back in, is
            the outcome the Challenge most rewards.
          </p>
        </Section>

        <Section title="Open and repeatable">
          <p>
            The project is released under the MIT license in a public
            repository. It runs at no cost and needs no API keys to operate or
            to review: the map uses a free keyless style, and when no
            language-model or GBIF credentials are present the tool degrades
            gracefully to a deterministic explanation and a manual
            copy-and-paste rule. The pipeline is seeded and deterministic, and
            the whole stack starts with a single command.
          </p>
        </Section>

        <section className="mt-12 max-w-3xl rounded-lg bg-panel p-8">
          <p className="text-sm leading-7 text-muted">
            Ready to try it? Open{" "}
            <a
              href="/explore"
              className="font-bold text-primary hover:underline"
            >
              Explore
            </a>{" "}
            to search a species and see its suspicious records, use{" "}
            <a
              href="/review"
              className="font-bold text-primary hover:underline"
            >
              Review
            </a>{" "}
            to confirm flagged groups and write them back to GBIF, or{" "}
            <a href="/clean" className="font-bold text-primary hover:underline">
              Clean my data
            </a>{" "}
            to check a file of your own.
          </p>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
