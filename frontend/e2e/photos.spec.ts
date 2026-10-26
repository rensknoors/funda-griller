import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

test("dossier shows foto-waarnemingen as geschat, citing photos the app serves itself", async ({ page }) => {
  await page.goto("/");
  const existing = page.getByRole("link", { name: "Buchterweg 15" });
  if (!(await existing.isVisible())) {
    await page.getByLabel("Funda-link").fill(LISTING_URL);
    await page.getByRole("button", { name: "Ophalen" }).click();
  }
  await page.getByRole("link", { name: "Buchterweg 15" }).click();

  const group = page.locator("details", { has: page.getByRole("heading", { name: "Foto-waarnemingen" }) });
  await expect(group.getByText("2 waarnemingen · 2 geschat")).toBeVisible();
  await expect(group.getByText("Keuken, geschatte leeftijd")).toBeVisible();
  await expect(group.getByText("≈ 12 jaar oud")).toBeVisible();
  await expect(group.getByLabel(/Waarneming, geschat door model, uit foto 2/)).toBeVisible();

  const thumbnails = group.getByRole("img");
  await expect(thumbnails).toHaveCount(2);
  for (const src of await thumbnails.evaluateAll((imgs) => imgs.map((img) => img.getAttribute("src")))) {
    expect(src).toMatch(/^\/api\/listings\/80907644\/photos\//);
  }

  await group.getByRole("button", { name: "Foto 2 bekijken" }).first().click();
  const viewer = page.getByRole("dialog", { name: "Foto 2" });
  await expect(viewer.getByRole("img", { name: "Foto 2" })).toBeVisible();
  await viewer.getByRole("button", { name: "Sluiten" }).click();
  await expect(viewer).toBeHidden();

  await group.getByRole("button", { name: "Foto's opnieuw analyseren" }).click();
  await expect(group.getByText("≈ 12 jaar oud")).toBeVisible();
  await expect(group.getByRole("alert")).toHaveCount(0);
});
