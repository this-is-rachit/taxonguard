"use client";

import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/Logo";

const NAV = [
  { label: "Explore", href: "/explore" },
  { label: "Review", href: "/review" },
  { label: "Clean my data", href: "/clean" },
  { label: "About", href: "/about" },
];

const GITHUB_URL = "https://github.com/this-is-rachit/taxonguard";

// The site header, shared by every page. The navigation links collapse into a
// menu button on small screens, so the whole site stays reachable on a phone.
export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-hairline">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link href="/" aria-label="TaxonGuard home">
          <Logo />
        </Link>

        <div className="flex items-center gap-4">
          <ul className="hidden items-center gap-8 md:flex">
            {NAV.map((item) => (
              <li key={item.label}>
                <Link
                  href={item.href}
                  className="text-sm font-bold text-ink hover:text-primary"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- intentional full load so the landing tour effect re-runs and reads ?tour=1 */}
          <a
            href="/?tour=1"
            className="hidden text-sm font-bold text-ink hover:text-primary md:inline-block"
          >
            Take a tour
          </a>
          <a
            href={GITHUB_URL}
            className="hidden rounded-md border border-hairline px-5 py-2 text-sm font-bold text-ink hover:border-primary hover:text-primary md:inline-block"
          >
            View on GitHub
          </a>

          <button
            type="button"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-hairline text-ink hover:border-primary md:hidden"
          >
            {open ? (
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M5 5l10 10M15 5L5 15"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M3 6h14M3 10h14M3 14h14"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </button>
        </div>
      </nav>

      {open ? (
        <div className="border-t border-hairline md:hidden">
          <ul className="mx-auto max-w-6xl px-6 py-2">
            {NAV.map((item) => (
              <li key={item.label}>
                <Link
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="block py-2 text-sm font-bold text-ink hover:text-primary"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- intentional full load so the landing tour effect re-runs and reads ?tour=1 */}
              <a
                href="/?tour=1"
                onClick={() => setOpen(false)}
                className="block py-2 text-sm font-bold text-ink hover:text-primary"
              >
                Take a tour
              </a>
            </li>
            <li>
              <a
                href={GITHUB_URL}
                className="block py-2 text-sm font-bold text-ink hover:text-primary"
              >
                View on GitHub
              </a>
            </li>
          </ul>
        </div>
      ) : null}
    </header>
  );
}
