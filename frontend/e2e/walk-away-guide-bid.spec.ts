import { expect, test } from "@playwright/test";

// Woningen of their own in the e2e app (see tests/e2e_app.py). Specs run in file order and this one
// runs after verdict.spec, whose "Dit verandert 1 oordeel" would otherwise count these Oordelen.
const GUIDE_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-2/80907660/";
const RESERVED_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-molenstraat-7/55500002/";
const TEMPO_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-4/80907661/";

const PROFILE = {
  household: [{ role: "adult", birth_date: "1988-04-12" }],
  gross_annual_income: 95000,
  assets: { savings: 100000, investments: 15000 },
  current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
  renovation_tolerance: 3,
};

// Asking € 595.000 against an expected sale price near € 420.000 (indexed WOZ): hoog ingezet, so 6% off.
// Kerkpad 2 has no price history, so its tempo is unknown and adds nothing.
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
  await expect(advies.getByText(/^Tempo onbekend:/)).toBeVisible();
  await expect(advies.getByText("Het Openingsbod blijft binnen 3% van het Richtbod.")).toBeVisible();
});

// Kerkpad 4 was listed 130 days ago at € 625.000 and now asks € 595.000: 6% + 2% + 1% off.
test("the Richtbod's breakdown shows the days on the market and the price reduction", async ({ page, request }) => {
  await request.put("/api/buyer-profile", { data: PROFILE });
  await request.post("/api/listings", { data: { url: TEMPO_URL } });
  await page.goto("/");
  await page.getByRole("link", { name: "Kerkpad 4" }).click();
  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();

  const advies = page.getByRole("region", { name: "Biedadvies" });
  await expect(advies.getByText(/Richtbod\s€\s382\.000: Vocht in de kelder\./)).toBeVisible();
  await advies.getByText("Hoe het Richtbod is berekend").click();
  await expect(advies.getByText("Dagen te koop: 130 dagen, 2%")).toBeVisible();
  await expect(advies.getByText(/^Prijsverlaging: van € 625\.000 naar € 595\.000, 1%$/)).toBeVisible();
  await expect(advies.getByText(/verwachte verkoopprijs min 9% korting/)).toBeVisible();
  await expect(advies.getByText(/Tempo onbekend/)).toBeHidden();
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
