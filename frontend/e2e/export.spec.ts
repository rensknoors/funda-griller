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

  const withProfile = page.getByRole("checkbox", { name: "Koperprofiel meesturen (geanonimiseerd)" });
  await expect(withProfile).toBeChecked();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Exporteer als Markdown" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^\d{4}-\d{2}-\d{2}-buchterweg-15-holtum\.md$/);
  const markdown = await readFile(await download.path(), "utf8");
  expect(markdown).toContain("# Dossier: Buchterweg 15, Holtum");
  expect(markdown).toContain("## Koperprofiel (geanonimiseerd)");

  await withProfile.uncheck();
  const [without] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Exporteer als Markdown" }).click(),
  ]);
  const plain = await readFile(await without.path(), "utf8");
  expect(plain).toContain("Koperprofiel meegestuurd: nee");
  expect(plain).not.toContain("## Koperprofiel (geanonimiseerd)");
});
