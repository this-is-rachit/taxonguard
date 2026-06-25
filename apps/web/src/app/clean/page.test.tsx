import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type CleanReport, postCleanUpload } from "@/lib/api";

import CleanPage from "./page";

vi.mock("@/lib/api", () => ({
  postCleanUpload: vi.fn(),
  cleanDownloadUrl: (path: string) => `http://api.test${path}`,
}));

const REPORT: CleanReport = {
  clean_id: "abc123",
  summary: {
    total_records: 6,
    flagged_records: 2,
    clean_records: 4,
    taxa: 1,
    checks_run: ["coordinate quality", "land/sea realm"],
    issues: [
      { label: "null-island coordinates (0, 0)", count: 1 },
      { label: "land/sea realm mismatch", count: 1 },
    ],
  },
  flagged: [
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
  ],
  flagged_truncated: false,
  download_url: "/clean/abc123/download",
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CleanPage />
    </QueryClientProvider>,
  );
}

function selectFile() {
  const input = screen.getByLabelText("Occurrence CSV file");
  const file = new File(
    ["gbifID,decimalLatitude,decimalLongitude\n1,0,0"],
    "occ.csv",
    {
      type: "text/csv",
    },
  );
  fireEvent.change(input, { target: { files: [file] } });
}

describe("Clean page", () => {
  beforeEach(() => {
    vi.mocked(postCleanUpload).mockReset();
  });

  it("disables the check button until a file is chosen", () => {
    renderPage();
    expect(screen.getByRole("button", { name: "Check file" })).toBeDisabled();
  });

  it("shows the before/after summary after a successful check", async () => {
    vi.mocked(postCleanUpload).mockResolvedValue(REPORT);
    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: "Check file" }));

    expect(await screen.findByText("Records checked")).toBeInTheDocument();
    expect(screen.getByText("Flagged as suspect")).toBeInTheDocument();
    expect(screen.getByText("coordinate quality")).toBeInTheDocument();
  });

  it("lists the flagged records with reasons", async () => {
    vi.mocked(postCleanUpload).mockResolvedValue(REPORT);
    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: "Check file" }));

    expect(await screen.findByText("Rana temporaria")).toBeInTheDocument();
    expect(screen.getByText("Null island")).toBeInTheDocument();
    expect(screen.getByText("Land/sea mismatch")).toBeInTheDocument();
  });

  it("offers a download link to the cleaned CSV", async () => {
    vi.mocked(postCleanUpload).mockResolvedValue(REPORT);
    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: "Check file" }));

    const link = await screen.findByRole("link", {
      name: "Download cleaned CSV",
    });
    expect(link).toHaveAttribute(
      "href",
      "http://api.test/clean/abc123/download",
    );
  });

  it("calls the API with the chosen file", async () => {
    vi.mocked(postCleanUpload).mockResolvedValue(REPORT);
    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: "Check file" }));

    await waitFor(() => expect(postCleanUpload).toHaveBeenCalledTimes(1));
    const arg = vi.mocked(postCleanUpload).mock.calls[0][0];
    expect(arg).toBeInstanceOf(File);
    expect(arg.name).toBe("occ.csv");
  });

  it("shows an error when the check fails", async () => {
    vi.mocked(postCleanUpload).mockRejectedValue(
      new Error("the file has no rows"),
    );
    renderPage();
    selectFile();
    fireEvent.click(screen.getByRole("button", { name: "Check file" }));

    expect(
      await screen.findByText("Could not check the file"),
    ).toBeInTheDocument();
    expect(screen.getByText("the file has no rows")).toBeInTheDocument();
  });
});
