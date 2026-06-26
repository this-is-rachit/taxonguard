import { expect, test } from "@playwright/test";

// All tests in this file run at a phone-sized viewport.
test.use({ viewport: { width: 390, height: 844 } });

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

test("mobile: the menu opens and navigates", async ({ page }) => {
  await page.goto("/");

  // The hamburger button is shown on small screens.
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("button", { name: "Close menu" })).toBeVisible();

  // The menu links are reachable; navigate to About through it.
  await page.getByRole("link", { name: "About" }).last().click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(
    page.getByRole("heading", { name: "How TaxonGuard works", level: 1 }),
  ).toBeVisible();
});

test("mobile: filters collapse into a disclosure", async ({ page }) => {
  await page.route(/\/clean$/, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ json: REPORT });
    } else {
      await route.continue();
    }
  });

  await page.goto("/clean");

  await page.getByLabel("Occurrence CSV file").setInputFiles({
    name: "occurrences.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("gbifID,decimalLatitude,decimalLongitude\n1,0,0\n"),
  });
  await page.getByRole("button", { name: "Check file" }).click();

  // The flagged record is shown.
  await expect(
    page.getByRole("table").getByText("Rana temporaria"),
  ).toBeVisible();

  // On a phone the facet rail is hidden behind a Filters button.
  const filters = page.getByRole("button", { name: "Filters" });
  await expect(filters).toBeVisible();
  await expect(page.getByText(/Minimum suspicion/)).toBeHidden();

  // Opening the disclosure reveals the controls.
  await filters.click();
  await expect(page.getByText(/Minimum suspicion/)).toBeVisible();
});
