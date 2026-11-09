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

for (const viewport of [
  { width: 1280, height: 800 },
  { width: 390, height: 844 },
]) {
  test(`the photo viewer covers the topbar at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    const existing = page.getByRole("link", { name: "Buchterweg 15" });
    if (!(await existing.isVisible())) {
      await page.getByLabel("Funda-link").fill(LISTING_URL);
      await page.getByRole("button", { name: "Ophalen" }).click();
    }
    await page.getByRole("link", { name: "Buchterweg 15" }).click();
    await page.getByRole("button", { name: "Foto 1 openen" }).click();

    const viewer = page.getByRole("dialog", { name: "Foto 1" });
    const topmostAt = (selector: string) =>
      page.locator(selector).first().evaluate((element) => {
        const box = element.getBoundingClientRect();
        const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
        return hit !== null && (element === hit || element.contains(hit));
      });
    await expect(viewer.getByRole("heading", { name: "Foto 1" })).toBeVisible();
    // Wait out the open transition before hit-testing.
    await expect(viewer).not.toHaveAttribute("data-starting-style");
    expect(await topmostAt('[role="dialog"] h2')).toBe(true);
    expect(await topmostAt('[role="dialog"] button:has-text("Sluiten")')).toBe(true);
    // The backdrop dims the topbar too.
    expect(await topmostAt(".topbar")).toBe(false);
  });
}
