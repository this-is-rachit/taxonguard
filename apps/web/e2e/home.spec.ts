import { expect, test } from "@playwright/test";

test("home page shows the product and key actions", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "TaxonGuard", level: 1 }),
  ).toBeVisible();

  await expect(page.getByRole("img", { name: "TaxonGuard" })).toBeVisible();

  await expect(
    page.getByRole("link", { name: "View on GitHub" }),
  ).toBeVisible();
});
