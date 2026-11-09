import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

test("a woning downloads as Markdown, with or without the anonymised koperprofiel", async ({ page, request }) => {
  await request.put("/api/buyer-profile", {
    data: {
      household: [{ role: "adult", birth_date: "1988-04-12" }],
      gross_annual_income: 95000,
      assets: { savings: 40000, investments: 15000 },
      renovation_tolerance: 3,
    },
  });
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await page.goto("/");
  await page.getByRole("link", { name: "Buchterweg 15" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();

  const exportMenu = page.getByRole("button", { name: "Exporteer als Markdown" });
  const withProfile = page.getByRole("menuitemcheckbox", { name: "Koperprofiel meesturen" });
  const downloadItem = page.getByRole("menuitem", { name: "Downloaden" });
  await exportMenu.click();
  await expect(withProfile).toBeChecked();
  const [download] = await Promise.all([page.waitForEvent("download"), downloadItem.click()]);
  expect(download.suggestedFilename()).toMatch(/^\d{4}-\d{2}-\d{2}-buchterweg-15-holtum\.md$/);
  const markdown = await readFile(await download.path(), "utf8");
  expect(markdown).toContain("# Dossier: Buchterweg 15, Holtum");
  expect(markdown).toContain("## Koperprofiel (geanonimiseerd)");

  await expect(downloadItem).toBeHidden();
  await exportMenu.click();
  // Unticking keeps the menu open, so Downloaden is one click further.
  await withProfile.click();
  await expect(withProfile).not.toBeChecked();
  const [without] = await Promise.all([page.waitForEvent("download"), downloadItem.click()]);
  const plain = await readFile(await without.path(), "utf8");
  expect(plain).toContain("Koperprofiel meegestuurd: nee");
  expect(plain).not.toContain("## Koperprofiel (geanonimiseerd)");
});
