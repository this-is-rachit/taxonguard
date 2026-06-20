import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TaxonGuard",
  description:
    "Detect, explain, expert-confirm, and write back implausible GBIF occurrence records.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
