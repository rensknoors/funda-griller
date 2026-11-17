import { expect, test } from "@playwright/test";

// A woning of its own: its comparables are fetched here, which the other specs's Buchterweg 15 must not see.
const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-hoogstraat-8/80907658/";

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
  await page.getByRole("link", { name: "Hoogstraat 8" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Hoogstraat 8" })).toBeVisible();

  // On the WOZ-waarde alone the verwachte verkoopprijs is weakly grounded: the Signaal is raised
  // for the oordeel to weigh, but it is no Harde afwijzing.
  await expect(page.getByRole("paragraph").filter({ hasText: "Harde afwijzing" })).toBeHidden();
  await expect(page.getByRole("region", { name: "Signalen" }).getByText("Verwachte verkoopprijs boven je betaalruimte")).toBeVisible();

  // With comparables it is strongly grounded, and the deal-breaker applies.
  const group = page.locator("details", { has: page.getByRole("heading", { name: "Vergelijkbare woningen" }) });
  await group.getByRole("button", { name: "Vergelijkbare woningen ophalen" }).click();
  await expect(group.getByText("5 vergelijkbare woningen", { exact: true })).toBeVisible();

  await expect(page.getByRole("paragraph").filter({ hasText: "Harde afwijzing" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Deal-breaker" })).toContainText("Deal-breaker: Boven budget");
  const signalen = page.getByRole("region", { name: "Signalen" });
  // The expected price beyond headroom, and the missing tuin.
  await expect(signalen.getByRole("heading", { name: /Minpunt \(2\)/ })).toBeVisible();

  await signalen.getByText("Verwachte verkoopprijs boven je betaalruimte").click();
  await expect(signalen.getByText("Regel expected_price_beyond_headroom · versie 1")).toBeVisible();
  await expect(signalen.getByText("Ruimte boven verwachte prijs")).toBeVisible();
});
