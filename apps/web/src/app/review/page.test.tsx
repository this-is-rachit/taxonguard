import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type ClusterDetail,
  type ClusterSummary,
  type DecisionResponse,
  getCluster,
  getClusters,
  postDecision,
} from "@/lib/api";

import ReviewPage from "./page";

vi.mock("@/lib/api", () => ({
  getClusters: vi.fn(),
  getCluster: vi.fn(),
  getTaxa: vi.fn(),
  postDecision: vi.fn(),
}));

vi.mock("@/components/review/ClusterMap", () => ({
  ClusterMap: () => <div data-testid="cluster-map" />,
}));

const SUMMARY: ClusterSummary = {
  cluster_id: "rana_temporaria:-4_0",
  taxon: "Rana temporaria",
  count: 2,
  max_score: 0.99,
  mean_score: 0.95,
  latitude: 0,
  longitude: 0,
  reason_counts: { realm_mismatch: 2, zero_coordinates: 1 },
  explanation: "This Rana temporaria record is flagged as suspicious.",
  decision: null,
};

const DETAIL: ClusterDetail = {
  ...SUMMARY,
  records: [
    {
      gbif_id: 1,
      latitude: 0,
      longitude: 0,
      suspicion_score: 0.99,
      confidence: 1,
      reasons: ["realm_mismatch", "zero_coordinates"],
    },
  ],
  rule: {
    taxon: "Rana temporaria",
    geometry: "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
    value: "suspicious",
    record_count: 2,
  },
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ReviewPage />
    </QueryClientProvider>,
  );
}

describe("Review page", () => {
  beforeEach(() => {
    vi.mocked(getClusters).mockReset();
    vi.mocked(getCluster).mockReset();
    vi.mocked(postDecision).mockReset();
  });

  it("lists clusters returned by the API", async () => {
    vi.mocked(getClusters).mockResolvedValue([SUMMARY]);
    renderPage();
    expect(await screen.findByText("Rana temporaria")).toBeInTheDocument();
    expect(screen.getByText("Land/sea mismatch")).toBeInTheDocument();
  });

  it("shows the draft rule when a cluster is selected", async () => {
    vi.mocked(getClusters).mockResolvedValue([SUMMARY]);
    vi.mocked(getCluster).mockResolvedValue(DETAIL);
    renderPage();

    const item = await screen.findByRole("button", {
      name: "Select Rana temporaria cluster",
    });
    fireEvent.click(item);

    expect(await screen.findByText("Draft rule")).toBeInTheDocument();
    expect(screen.getByText(/POLYGON/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no clusters", async () => {
    vi.mocked(getClusters).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No flagged clusters")).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    vi.mocked(getClusters).mockRejectedValue(new Error("boom"));
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("Could not reach the API")).toBeInTheDocument(),
    );
  });

  it("lists the records of a selected cluster", async () => {
    vi.mocked(getClusters).mockResolvedValue([SUMMARY]);
    vi.mocked(getCluster).mockResolvedValue(DETAIL);
    renderPage();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Select Rana temporaria cluster",
      }),
    );
    expect(await screen.findByText("GBIF 1")).toBeInTheDocument();
  });

  it("posts a decision when Confirm is clicked", async () => {
    vi.mocked(getClusters).mockResolvedValue([SUMMARY]);
    vi.mocked(getCluster).mockResolvedValue(DETAIL);
    const response: DecisionResponse = {
      cluster_id: SUMMARY.cluster_id,
      decision: {
        action: "confirm",
        value: "suspicious",
        note: null,
        written_to_gbif: false,
      },
      status: "recorded",
    };
    vi.mocked(postDecision).mockResolvedValue(response);
    renderPage();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Select Rana temporaria cluster",
      }),
    );
    const confirm = await screen.findByRole("button", { name: "Confirm" });
    fireEvent.click(confirm);

    await waitFor(() =>
      expect(postDecision).toHaveBeenCalledWith(SUMMARY.cluster_id, {
        action: "confirm",
        note: null,
      }),
    );
  });

  it("shows a recorded decision on the cluster", async () => {
    vi.mocked(getClusters).mockResolvedValue([SUMMARY]);
    vi.mocked(getCluster).mockResolvedValue({
      ...DETAIL,
      decision: {
        action: "confirm",
        value: "suspicious",
        note: null,
        written_to_gbif: false,
      },
    });
    renderPage();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Select Rana temporaria cluster",
      }),
    );
    expect(await screen.findByText(/Recorded:/)).toBeInTheDocument();
    expect(screen.getByText(/Not yet written to/)).toBeInTheDocument();
  });

  it("links to the annotation when a decision is written to GBIF", async () => {
    vi.mocked(getClusters).mockResolvedValue([SUMMARY]);
    vi.mocked(getCluster).mockResolvedValue({
      ...DETAIL,
      decision: {
        action: "confirm",
        value: "suspicious",
        note: null,
        written_to_gbif: true,
        annotation_id: 99,
        annotation_url:
          "https://labs.gbif.org/occurrence/experimental/annotation/rule/99",
        manual_instructions: null,
      },
    });
    renderPage();

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Select Rana temporaria cluster",
      }),
    );
    expect(await screen.findByText(/Written to GBIF/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "View the annotation" });
    expect(link).toHaveAttribute(
      "href",
      "https://labs.gbif.org/occurrence/experimental/annotation/rule/99",
    );
  });
});
