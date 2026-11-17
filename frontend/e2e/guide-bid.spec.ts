import { expect, test } from "@playwright/test";

// Woningen of their own in the e2e app (see tests/e2e_app.py): the Oordelen here must not count in
// the other specs' "Dit verandert N oordelen".
const GUIDE_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-2/80907660/";
const RESERVED_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-molenstraat-7/55500002/";

const PROFILE = {
  household: [{ role: "adult", birth_date: "1988-04-12" }],
  gross_annual_income: 95000,
  assets: { savings: 100000, investments: 15000 },
  current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
  renovation_tolerance: 3,
};

// Asking € 595.000 against an expected sale price near € 420.000 (indexed WOZ): hoog ingezet, so 6% off.
test("the Biedadvies shows the Richtbod and how its discount came about", async ({ page, request }) => {
  await request.put("/api/buyer-profile", { data: PROFILE });
  await request.post("/api/listings", { data: { url: GUIDE_URL } });
  await page.goto("/");
  await page.getByRole("link", { name: "Kerkpad 2" }).click();
  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();

  const advies = page.getByRole("region", { name: "Biedadvies" });
  await expect(advies.getByText(/Richtbod\s€\s395\.000: Vocht in de kelder\./)).toBeVisible();
  await advies.getByText("Hoe het Richtbod is berekend").click();
  await expect(advies.getByText("Prijsstelling: hoog ingezet, 6%")).toBeVisible();
  await expect(advies.getByText("Het Openingsbod blijft binnen 3% van het Richtbod.")).toBeVisible();
});

test("a house sold under reservation gets conditions and a note, no bids", async ({ page, request }) => {
  await request.put("/api/buyer-profile", { data: PROFILE });
  await request.post("/api/listings", { data: { url: RESERVED_URL } });
  await page.goto("/");
  await page.getByRole("link", { name: "Molenstraat 7" }).click();
  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();

  const advies = page.getByRole("region", { name: "Biedadvies" });
  await expect(advies.getByText("Verkocht onder voorbehoud:")).toBeVisible();
  await expect(advies.getByText("Reserveringslijst opvragen")).toBeVisible();
  await expect(advies.getByText("Openingsbod", { exact: true })).toBeHidden();
});
