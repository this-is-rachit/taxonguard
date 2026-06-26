import { type Driver, driver } from "driver.js";

// True when the user has asked the operating system to reduce motion. The tour
// then runs without its slide-and-fade transitions.
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

// A short, plain-language tour of the landing page for a first-time visitor. It
// anchors to elements marked with data-tour, so it degrades gracefully if any
// are absent. driver.js handles focus, keyboard navigation, and Escape to close.
export function startSiteTour(onDone?: () => void): Driver {
  const tour = driver({
    showProgress: true,
    animate: !prefersReducedMotion(),
    allowClose: true,
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: "Done",
    popoverClass: "tg-tour",
    onDestroyed: () => {
      onDone?.();
    },
    steps: [
      {
        popover: {
          title: "Welcome to TaxonGuard",
          description:
            "TaxonGuard finds species records in GBIF that cannot be right, explains why, and lets an expert send a correction back to GBIF. Here is a quick tour.",
        },
      },
      {
        element: '[data-tour="search"]',
        popover: {
          title: "Search a species",
          description:
            "Type any species name. TaxonGuard fetches its records from GBIF and flags the ones that do not fit, with a plain reason and a score for each.",
          side: "bottom",
          align: "start",
        },
      },
      {
        element: '[data-tour="demos"]',
        popover: {
          title: "Or try a demo",
          description:
            "New to it? Click one of these species to see real results straight away, without typing anything.",
          side: "bottom",
          align: "start",
        },
      },
      {
        element: '[data-tour="how-it-works"]',
        popover: {
          title: "How it works",
          description:
            "TaxonGuard detects implausible records, explains each one in a single sentence, and writes a confirmed fix back to GBIF so every data user benefits.",
          side: "top",
          align: "start",
        },
      },
      {
        element: '[data-tour="how-to"]',
        popover: {
          title: "Three ways to use it",
          description:
            "Explore any species, Review groups of flagged records and confirm them, or Clean a file of your own. You can reach all three from the menu at any time.",
          side: "top",
          align: "start",
        },
      },
      {
        popover: {
          title: "You are ready",
          description:
            "Pick a demo species or search for one to begin. You can replay this tour any time from the Take a tour button in the header.",
        },
      },
    ],
  });

  tour.drive();
  return tour;
}
