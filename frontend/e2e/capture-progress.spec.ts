import { expect, test } from "@playwright/test";

// The e2e backend's fake provider knows this one; no other spec captures it.
const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-43/80907653/";

test("a capture runs in the background and reports its progress on every page", async ({ page }) => {
  // Hold the capture's request open, as a slow provider would.
  let release = () => {};
  const released = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/listings", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await released;
    await route.continue();
  });
  await page.goto("/");
  await page.getByLabel("Funda-link").fill(LISTING_URL);
  await page.getByRole("button", { name: "Ophalen", exact: true }).click();

  const tray = page.getByRole("region", { name: "Ophalen" });
  await expect(page.getByLabel("Funda-link")).toHaveValue("");
  await expect(tray.getByText("Dorpsstraat 43")).toBeVisible();
  await expect(tray.getByText(/Stap 1 van 5: Advertentie ophalen/)).toBeVisible();

  await page.getByRole("navigation", { name: "Hoofdmenu" }).getByRole("link", { name: "Koperprofiel" }).click();
  await expect(tray.getByText(/Stap 1 van 5/)).toBeVisible();

  release();
  await expect(tray.getByText("Opgehaald.")).toBeVisible();
  await tray.getByRole("link", { name: "Dossier openen" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Dorpsstraat 43" })).toBeVisible();
  await expect(tray).toBeHidden();
});
