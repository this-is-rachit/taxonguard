# Compliance with the GBIF Ebbe Nielsen Challenge rules

This document maps TaxonGuard build decisions to the official Challenge rules.
It is the gate every build step is checked against. The text below tracks the
2026 Official Rules as the working template. The 2027 round rules are not
published yet; GBIF keeps them stable year to year, so this is a safe proxy.
Items that could change for 2027 are marked.

## Timing

- 2026 submission period: 27 January 2026 to 26 June 2026, 23:59 CEST.
- Target round: 2027. The 2027 window is expected to open around late
  January 2027. This file will be updated when 2027 rules are published.

## Hard requirements

1. Zero cost to judges. Judges must access, operate, or review the submission
   at no cost on readily available hardware.
   - Free data only: GBIF API, WorldClim, Natural Earth.
   - No GPU. Models are CPU-only and cached per taxon.
   - Free-tier hosting for the live demo.
   - One-command Docker Compose local run, no secret keys required to review.
   - The language-model explanation layer has a deterministic no-key fallback,
     so the whole tool works with no paid API.

2. Openness and repeatability (judging criterion and hard requirement).
   - MIT license, public repository.
   - A reproducible notebook regenerates the key results.
   - Seeded, deterministic pipeline.
   - Documented operating instructions in `docs/operating-instructions.md`.

3. Novelty and timing.
   - A significant portion of the submission must be developed for the
     Challenge. Work developed before the start date is not eligible.
   - We start now but target 2027. Plan so a significant, demonstrable portion
     of new development lands inside the official 2027 window, with
     git-timestamped commits as the evidence.
   - This point is ambiguous. The rules invite written clarification. Action:
     email ENChallenge@gbif.org to confirm the timing interpretation before
     relying on it. This note is the plain reading of the rules, not legal
     advice.

4. Data licenses and citation.
   - Pull occurrence data through the GBIF download or SQL API to get a DOI'd,
     citable subset, then cite that DOI in the repo and submission.
   - Document the WorldClim and Natural Earth licenses. Every data source gets
     a line naming its license in `docs/data-sources.md`.

5. No third-party trademarks or copyrighted material in any entry material,
   including the video.
   - Demo video uses royalty-free or original music only.
   - No logos we do not have rights to. We do not imply official GBIF
     endorsement. The product name is TaxonGuard, not a GBIF-branded name.

## Required deliverables (shape the build from the start)

- A video showing inputs, process, and outputs.
- A written description covering innovation, impact, tools used, and how GBIF
  data is used.
- Operating instructions and technical requirements.
- Repository link.
- An abstract of at most 1,000 words, in English.
- Judges may score from the text and video alone, so the demo flow must read
  clearly on camera and the written narrative must stand on its own. Keep a
  draft abstract and operating-instructions doc in the repo from early on.

## Eligibility (confirm before submission)

- Confirm no team member is GBIF Secretariat staff, a contractor, a Science
  Committee member, or a Head of Delegation.
- Decide solo versus team early. A team must name one Representative who
  submits and receives any prize.

## Intellectual property (awareness only)

- Entering grants GBIF a nonexclusive, royalty-free license to use and display
  the submission. The work stays ours. MIT already aligns with this.

## Submission checklist (filled in near the end)

- [ ] Public GitHub repository, MIT license, real README, reproducible notebook.
- [ ] Live demo reachable in a clean browser with no keys.
- [ ] A few confirmed rules visible in GBIF's annotation system, or the
      documented manual fallback shown.
- [ ] Three-to-five-minute video that opens on the live loop.
- [ ] Abstract and rationale, maximum 1,000 words.
- [ ] Entry form fields ready: title, team and affiliations, abstract and
      rationale, operating instructions, video link, repository link.
- [ ] All materials in English.
