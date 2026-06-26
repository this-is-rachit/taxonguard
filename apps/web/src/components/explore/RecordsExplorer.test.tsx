import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type AnnotateResponse,
  type CleanRecord,
  postAnnotate,
} from "@/lib/api";

import { RecordsExplorer } from "./RecordsExplorer";

vi.mock("@/lib/api", () => ({
  postAnnotate: vi.fn(),
}));

vi.mock("@/components/explore/RecordsMap", () => ({
  RecordsMap: () => <div data-testid="records-map" />,
}));

const RECORDS: CleanRecord[] = [
  {
    gbif_id: 3,
    scientific_name: "Rana temporaria",
    latitude: 0,
    longitude: 0,
    flagged: true,
    suspicion_score: 0.99,
    confidence: 1,
    reasons: ["zero_coordinates"],
  },
  {
    gbif_id: 6,
    scientific_name: "Rana temporaria",
    latitude: 12.34,
    longitude: -40,
    flagged: true,
    suspicion_score: 0.9,
    confidence: 1,
    reasons: ["realm_mismatch"],
  },
];

const SUMMARY = {
  total_records: 2,
  flagged_records: 2,
  clean_records: 0,
  taxa: 1,
  checks_run: ["coordinate quality"],
  issues: [{ label: "Null island", count: 1 }],
};

function wrap(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  );
}

describe("RecordsExplorer write-back", () => {
  beforeEach(() => {
    vi.mocked(postAnnotate).mockReset();
  });

  it("hides the write-back panel when no taxon is given (Clean screen)", () => {
    wrap(<RecordsExplorer records={RECORDS} summary={SUMMARY} showTaxon />);
    expect(screen.queryByText("Write back to GBIF")).not.toBeInTheDocument();
  });

  it("proposes a rule over the filtered records and shows the published result", async () => {
    const response: AnnotateResponse = {
      submitted: true,
      rule: {
        taxon: "Rana temporaria",
        geometry: "POLYGON ((0 0, 1 1, 2 0, 0 0))",
        value: "suspicious",
        record_count: 2,
      },
      written_to_gbif: true,
      annotation_id: 99,
      annotation_url:
        "https://api.gbif.org/v1/occurrence/experimental/annotation/rule/99",
    };
    vi.mocked(postAnnotate).mockResolvedValue(response);

    wrap(
      <RecordsExplorer
        records={RECORDS}
        summary={SUMMARY}
        taxonLabel="Rana temporaria"
        annotateTaxon="Rana temporaria"
      />,
    );

    expect(screen.getByText("Write back to GBIF")).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Propose a GBIF rule" }),
    );

    expect(await screen.findByText(/Published to GBIF/)).toBeInTheDocument();
    await waitFor(() =>
      expect(postAnnotate).toHaveBeenCalledWith({
        taxon: "Rana temporaria",
        points: [
          { latitude: 0, longitude: 0 },
          { latitude: 12.34, longitude: -40 },
        ],
      }),
    );
    expect(
      screen.getByRole("link", { name: "View the annotation" }),
    ).toBeInTheDocument();
  });

  it("shows the manual fallback when GBIF credentials are absent", async () => {
    const response: AnnotateResponse = {
      submitted: false,
      rule: {
        taxon: "Rana temporaria",
        geometry: "POLYGON ((0 0, 1 1, 2 0, 0 0))",
        value: "suspicious",
        record_count: 2,
      },
      written_to_gbif: false,
      manual_instructions:
        "Taxon: Rana temporaria\nAnnotation: SUSPICIOUS\nGeometry (WKT): POLYGON ((0 0, 1 1, 2 0, 0 0))",
    };
    vi.mocked(postAnnotate).mockResolvedValue(response);

    wrap(
      <RecordsExplorer
        records={RECORDS}
        summary={SUMMARY}
        taxonLabel="Rana temporaria"
        annotateTaxon="Rana temporaria"
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Propose a GBIF rule" }),
    );
    expect(
      await screen.findByText(/no GBIF credentials are configured/),
    ).toBeInTheDocument();
  });
});
