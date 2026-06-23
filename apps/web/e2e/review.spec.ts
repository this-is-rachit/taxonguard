import { expect, test } from "@playwright/test";

// Fixtures mirroring the API response shapes.
const SUMMARY = {
  cluster_id: "rana_temporaria:-4_0",
  taxon: "Rana temporaria",
  count: 2,
  max_score: 0.99,
  mean_score: 0.95,
  latitude: 0,
  longitude: 0,
  reason_counts: { realm_mismatch: 2, zero_coordinates: 1 },
  explanation: "This Rana temporaria record is flagged as suspicious.",
  decision: null as unknown,
};

const DETAIL = {
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

const RECORDED = {
  action: "confirm",
  value: "suspicious",
  note: null,
  written_to_gbif: false,
};

test("review loop: pick a cluster and confirm its rule", async ({ page }) => {
  let confirmed = false;

  // Keep MapLibre offline with a minimal empty style.
  await page.route(/maplibre\.org\/.*/, async (route) => {
    const isStyle = route.request().url().endsWith("style.json");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: isStyle
        ? JSON.stringify({ version: 8, sources: {}, layers: [] })
        : "{}",
    });
  });

  // Mock the API.
  await page.route(/\/clusters(\?.*)?$/, (route) =>
    route.fulfill({ json: [SUMMARY] }),
  );
  await page.route(/\/clusters\/[^/]+$/, (route) =>
    route.fulfill({
      json: { ...DETAIL, decision: confirmed ? RECORDED : null },
    }),
  );
  await page.route(/\/clusters\/[^/]+\/decision$/, (route) => {
    confirmed = true;
    route.fulfill({
      json: {
        cluster_id: SUMMARY.cluster_id,
        decision: RECORDED,
        status: "recorded",
      },
    });
  });

  await page.goto("/review");

  // The map and the cluster list render.
  await expect(
    page.getByRole("region", { name: "Map of flagged clusters" }),
  ).toBeVisible();
  await expect(page.getByText("Rana temporaria").first()).toBeVisible();

  // Select the cluster and see its detail.
  await page
    .getByRole("button", { name: "Select Rana temporaria cluster" })
    .click();
  await expect(page.getByText("Draft rule", { exact: true })).toBeVisible();
  await expect(page.getByText("GBIF 1", { exact: true })).toBeVisible();
  await expect(page.getByText(/POLYGON/)).toBeVisible();

  // Confirm the rule and see the recorded decision.
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText(/Recorded:/)).toBeVisible();
  await expect(page.getByText(/Not yet written to/)).toBeVisible();
});
