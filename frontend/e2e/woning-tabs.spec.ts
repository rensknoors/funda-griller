import { expect, type Page, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

async function openDossier(page: Page) {
  await page.goto("/");
  const existing = page.getByRole("link", { name: "Buchterweg 15" });
  if (!(await existing.isVisible())) {
    await page.getByLabel("Funda-link").fill(LISTING_URL);
    await page.getByRole("button", { name: "Ophalen" }).click();
  }
  await page.getByRole("link", { name: "Buchterweg 15" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();
  // The Dossier body loads after the header; scroll only once the page has its full length.
  await expect(page.getByRole("complementary", { name: "Overzicht" })).toBeVisible();
  // Let the photo's flight into the header finish; the page is only a picture until then.
  await expect(page.locator("html")).not.toHaveAttribute("data-transition");
}

for (const viewport of [
  { width: 1280, height: 800 },
  { width: 390, height: 844 },
]) {
  test(`the Dossier/Oordeel tabs stay pinned under the topbar at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openDossier(page);
    const tabs = page.getByRole("navigation", { name: "Woning" });
    await expect(tabs).not.toHaveAttribute("data-stuck");

    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await expect(tabs).toHaveAttribute("data-stuck", "");
    const oordeel = tabs.getByRole("link", { name: "Oordeel", exact: true });
    await expect(oordeel).toBeInViewport();
    // Wait out the shrink before hit-testing.
    await expect.poll(() => tabs.evaluate((nav) => nav.getBoundingClientRect().height)).toBeLessThan(50);
    const topbarBottom = await page.locator(".topbar").evaluate((bar) => bar.getBoundingClientRect().bottom);
    // Pinned flush under the topbar, its hairline drawn over the bar's top pixel.
    const tabsTop = await tabs.evaluate((nav) => nav.getBoundingClientRect().top);
    expect(Math.abs(tabsTop - topbarBottom)).toBeLessThanOrEqual(1);
    expect(
      await oordeel.evaluate((link) => {
        const box = link.getBoundingClientRect();
        const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
        return hit !== null && (link === hit || link.contains(hit));
      }),
    ).toBe(true);

    await oordeel.click();
    await expect(page.getByRole("heading", { name: "Oordeel: Buchterweg 15" })).toBeVisible();
  });
}

test("an Op deze pagina link lands its heading below the pinned tabs", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await openDossier(page);
  const links = page.getByRole("navigation", { name: "Op deze pagina" }).getByRole("link");
  const last = links.last();
  const target = (await last.getAttribute("href"))!.slice(1);
  await last.click();

  const tabs = page.getByRole("navigation", { name: "Woning" });
  await expect(tabs).toHaveAttribute("data-stuck", "");
  await expect.poll(() => tabs.evaluate((nav) => nav.getBoundingClientRect().height)).toBeLessThan(50);
  const tabsBottom = await tabs.evaluate((nav) => nav.getBoundingClientRect().bottom);
  const headingTop = await page
    .locator(`[id="${target}"]`)
    .evaluate((section) => (section.querySelector("h2") ?? section).getBoundingClientRect().top);
  expect(headingTop).toBeGreaterThanOrEqual(tabsBottom);
});
