"use client";

import "driver.js/dist/driver.css";

import { useEffect, useState } from "react";

import { startSiteTour } from "@/lib/tour";

const SEEN_KEY = "taxonguard.tour.seen";

function markSeen() {
  try {
    window.localStorage.setItem(SEEN_KEY, "1");
  } catch {
    /* localStorage may be unavailable; the tour simply shows again next time */
  }
}

// Shows a one-time welcome card offering a guided tour, and starts the tour on
// request. It also starts the tour immediately when the page is opened with
// ?tour=1, which is how the header "Take a tour" button replays it from any page.
export function WelcomeTour() {
  const [showCard, setShowCard] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const wantsTour = params.get("tour") === "1";

    if (wantsTour) {
      // Clean the URL so a refresh does not restart the tour, then run it.
      window.history.replaceState(null, "", window.location.pathname);
      markSeen();
      startSiteTour();
      return;
    }

    let seen = false;
    try {
      seen = window.localStorage.getItem(SEEN_KEY) === "1";
    } catch {
      seen = false;
    }
    if (!seen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time client-only check on mount
      setShowCard(true);
    }
  }, []);

  function take() {
    markSeen();
    setShowCard(false);
    startSiteTour();
  }

  function skip() {
    markSeen();
    setShowCard(false);
  }

  if (!showCard) return null;

  return (
    <div
      role="dialog"
      aria-label="Welcome to TaxonGuard"
      className="tg-welcome fixed bottom-4 right-4 z-40 w-80 max-w-[calc(100vw-2rem)] rounded-lg border border-hairline bg-white p-4 shadow-lg"
    >
      <p className="text-sm font-bold text-ink">New here?</p>
      <p className="mt-1 text-sm leading-6 text-muted">
        Take a quick tour to see how TaxonGuard finds and fixes implausible
        species records.
      </p>
      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={take}
          className="rounded-md bg-secondary px-4 py-2 text-sm font-bold text-white hover:opacity-90"
        >
          Take the tour
        </button>
        <button
          type="button"
          onClick={skip}
          className="rounded-md px-3 py-2 text-sm font-bold text-muted hover:text-ink"
        >
          Skip tour
        </button>
      </div>
    </div>
  );
}
