import { expect, test } from "@playwright/test";

const CHANGING_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-markt-3/55500001/";

test("a sold woning says Verkocht in the dossier and on the oordeel", async ({ page, request }) => {
  // Available on first fetch, sold on every refetch after (see tests/e2e_app.py).
  await request.post("/api/listings", { data: { url: CHANGING_URL } });
  await request.post("/api/listings/55500001/refetch");
  await request.post("/api/listings/55500001/restore");

  await page.goto("/");
  await page.getByRole("button", { name: "Markt 3" }).click();

  const dossier = page.getByRole("region", { name: "Dossier: Markt 3" });
  await expect(dossier.locator("header").getByText("Verkocht")).toBeVisible();
  await expect(dossier.getByRole("listitem").filter({ hasText: "Status" }).getByText("Verkocht")).toBeVisible();

  await page.getByRole("button", { name: "Oordeel bekijken" }).click();
  await expect(page.getByText("Deze woning is verkocht. Een biedadvies is niet meer van toepassing.")).toBeVisible();
});
