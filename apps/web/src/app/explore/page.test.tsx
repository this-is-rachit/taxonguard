import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type SpeciesScoreReport, scoreTaxon, suggestSpecies } from "@/lib/api";

import ExplorePage from "./page";

vi.mock("@/lib/api", () => ({
  suggestSpecies: vi.fn(),
  scoreTaxon: vi.fn(),
}));

vi.mock("@/components/explore/RecordsMap", () => ({
  RecordsMap: () => <div data-testid="records-map" />,
}));

const REPORT: SpeciesScoreReport = {
  taxon: "Rana temporaria",
  summary: {
    total_records: 5,
    flagged_records: 2,
    clean_records: 3,
    taxa: 1,
    checks_run: ["coordinate quality", "land/sea realm", "climate niche"],
    issues: [
      { label: "null-island coordinates (0, 0)", count: 1 },
      { label: "land/sea realm mismatch", count: 1 },
    ],
  },
  records: [
    {
      gbif_id: 3,
      scientific_name: "Rana temporaria",
      latitude: 0,
      longitude: 0,
      flagged: true,
      suspicion_score: 0.99,
      confidence: 1,
      reasons: ["realm_mismatch", "zero_coordinates"],
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
    {
      gbif_id: 1,
      scientific_name: "Rana temporaria",
      latitude: 51.5,
      longitude: -0.12,
      flagged: false,
      suspicion_score: 0.0,
      confidence: 0.5,
      reasons: [],
    },
  ],
  records_truncated: false,
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ExplorePage />
    </QueryClientProvider>,
  );
}

describe("Explore page", () => {
  beforeEach(() => {
    vi.mocked(suggestSpecies).mockReset();
    vi.mocked(scoreTaxon).mockReset();
    vi.mocked(suggestSpecies).mockResolvedValue([]);
  });

  it("scores a species when an example is clicked", async () => {
    vi.mocked(scoreTaxon).mockResolvedValue(REPORT);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rana temporaria" }));

    expect(await screen.findByText(/2 shown/)).toBeInTheDocument();
    await waitFor(() =>
      expect(scoreTaxon).toHaveBeenCalledWith("Rana temporaria"),
    );
  });

  it("shows the summary view with counts", async () => {
    vi.mocked(scoreTaxon).mockResolvedValue(REPORT);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rana temporaria" }));
    await screen.findByText(/2 shown/);

    fireEvent.click(screen.getByRole("tab", { name: "summary" }));
    expect(await screen.findByText("Records scanned")).toBeInTheDocument();
    expect(screen.getByText("Issues by type")).toBeInTheDocument();
  });

  it("opens a detail panel when a row is clicked", async () => {
    vi.mocked(scoreTaxon).mockResolvedValue(REPORT);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rana temporaria" }));
    await screen.findByText(/2 shown/);

    // Click the reason badge inside the table (the facet rail has the same
    // label, so scope the query to the table).
    const table = await screen.findByRole("table");
    fireEvent.click(within(table).getByText("Null island"));
    expect(await screen.findByText("Why it is flagged")).toBeInTheDocument();
  });

  it("offers reason facets with counts", async () => {
    vi.mocked(scoreTaxon).mockResolvedValue(REPORT);
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rana temporaria" }));
    await screen.findByText(/2 shown/);

    // Two records carry realm mismatch at the default threshold.
    const facet = await screen.findByRole("button", {
      name: /Land\/sea mismatch/,
    });
    expect(facet).toHaveTextContent("2");
  });

  it("suggests species names from the search box", async () => {
    vi.mocked(suggestSpecies).mockResolvedValue([
      { key: 1, name: "Bufo bufo", rank: "SPECIES", kingdom: "Animalia" },
    ]);
    vi.mocked(scoreTaxon).mockResolvedValue({ ...REPORT, taxon: "Bufo bufo" });
    renderPage();

    fireEvent.change(screen.getByLabelText("Search a species"), {
      target: { value: "bufo" },
    });
    const option = await screen.findByText("Bufo bufo");
    fireEvent.click(option);

    await waitFor(() => expect(scoreTaxon).toHaveBeenCalledWith("Bufo bufo"));
  });

  it("shows an error when scoring fails", async () => {
    vi.mocked(scoreTaxon).mockRejectedValue(
      new Error("GBIF returned no records"),
    );
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Rana temporaria" }));

    expect(
      await screen.findByText("Could not score this species"),
    ).toBeInTheDocument();
  });
});
