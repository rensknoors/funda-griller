import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

test("dossier groups signalen and shows the deal-breaker behind a harde afwijzing", async ({
  page,
  request,
}) => {
  await request.put("/api/buyer-profile", {
    data: {
      household: [{ role: "adult", birth_date: "1988-04-12" }],
      gross_annual_income: 42000,
      assets: { savings: 12000, investments: 0 },
      must_haves: ["Tuin"],
      deal_breakers: ["Boven budget"],
      renovation_tolerance: 3,
    },
  });
  // Captured already when another spec ran first; a 409 is fine.
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await page.goto("/");
  await page.getByRole("button", { name: "Buchterweg 15" }).click();

  await expect(page.getByText("Harde afwijzing")).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Deal-breaker: Boven budget");
  const signalen = page.getByRole("region", { name: "Signalen" });
  // Headroom, missing tuin, and the asking price far above the fixture WOZ.
  await expect(signalen.getByRole("heading", { name: /Minpunt \(3\)/ })).toBeVisible();
  await expect(signalen.getByText("Vraagprijs ver boven de WOZ-waarde")).toBeVisible();

  await signalen.getByText("Vraagprijs boven je betaalruimte").click();
  await expect(signalen.getByText("Regel ask_beyond_headroom · versie 1")).toBeVisible();
  await expect(signalen.getByRole("link", { name: /Zie vak \d+/ })).toBeVisible();
});
