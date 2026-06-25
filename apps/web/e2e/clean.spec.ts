import { expect, test } from "@playwright/test";

// Mirrors the /clean report shape from the API.
const REPORT = {
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

test("clean my data: upload a file and see the flagged records", async ({
  page,
}) => {
  // Mock the upload endpoint; let everything else pass through.
  await page.route(/\/clean$/, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ json: REPORT });
    } else {
      await route.continue();
    }
  });

  await page.goto("/clean");

  // The check button is disabled until a file is chosen.
  await expect(page.getByRole("button", { name: "Check file" })).toBeDisabled();

  // Choose an in-memory CSV and run the check.
  await page.getByLabel("Occurrence CSV file").setInputFiles({
    name: "occurrences.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("gbifID,decimalLatitude,decimalLongitude\n1,0,0\n"),
  });
  await page.getByRole("button", { name: "Check file" }).click();

  // The flagged record appears in the default table view (scope to the table,
  // since the facet rail repeats the reason labels).
  const table = page.getByRole("table");
  await expect(table.getByText("Rana temporaria")).toBeVisible();
  await expect(table.getByText("Null island")).toBeVisible();

  // The summary is a view tab.
  await page.getByRole("tab", { name: "summary" }).click();
  await expect(page.getByText("Records scanned")).toBeVisible();
  await expect(page.getByText("Flagged as suspect")).toBeVisible();

  // The cleaned-CSV download is offered.
  await expect(
    page.getByRole("link", { name: "Download cleaned CSV" }),
  ).toHaveAttribute("href", /\/clean\/abc123\/download$/);
});
