"use client";

import { useEffect, useRef, useState } from "react";

// A small "?" control that reveals a one or two sentence hint about a nearby
// control. Accessible: a labelled button with aria-expanded, a tooltip region,
// and dismissal on Escape or a click outside. The hint text is plain, matching
// the rest of the interface copy.
export function HelpTip({ label, text }: { label: string; text: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span ref={ref} className="relative inline-flex align-middle">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-hairline text-[10px] font-bold leading-none text-muted hover:border-primary hover:text-primary"
      >
        ?
      </button>
      {open ? (
        <span
          role="tooltip"
          className="absolute left-6 top-0 z-20 w-60 rounded-md border border-hairline bg-white p-3 text-xs font-normal leading-5 text-muted shadow-sm"
        >
          {text}
        </span>
      ) : null}
    </span>
  );
}
