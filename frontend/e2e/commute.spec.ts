import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-41/80907651/";
const PROFILE = {
  household: [{ role: "adult", birth_date: "1988-04-12" }],
  gross_annual_income: 95000,
  assets: { savings: 40000, investments: 15000 },
  renovation_tolerance: 3,
};
const WERK = { label: "Werk", address: "Kantoorlaan 1, Eindhoven", max_minutes: 45 };

test("dossier shows the reistijd per pendelbestemming and a minpunt when it is too far", async ({
  page,
  request,
}) => {
  const sport = { label: "Sport", address: "Nergensweg 1, Nergens", max_minutes: 20 };
  await request.put("/api/buyer-profile", { data: { ...PROFILE, commute_destinations: [WERK, sport] } });
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await page.goto("/");
  await page.getByRole("button", { name: "Dorpsstraat 41" }).click();

  await expect(page.getByText(/Reistijd: gelukt/)).toBeVisible();
  const reistijd = page.locator("details", { has: page.getByRole("heading", { name: "Reistijd" }) });
  await expect(reistijd.getByText("Reistijd naar Werk")).toBeVisible();
  await expect(
    reistijd.getByText("52 min met de auto (fiets 140 min), openbaar vervoer niet meegerekend"),
  ).toBeVisible();
  await expect(reistijd.getByLabel(/Bron: Reistijd, onofficieel, opgehaald/).first()).toBeVisible();
  // A destination the geocoder cannot place is shown as unknown, not dropped.
  await expect(reistijd.getByText("Reistijd naar Sport")).toBeVisible();
  await expect(reistijd.getByText("onbekend: adres niet gevonden")).toBeVisible();

  const signalen = page.getByRole("region", { name: "Signalen" });
  await signalen.getByText("Reistijd boven je maximum: Werk").click();
  await expect(signalen.getByText("Regel commute_too_long · versie 2")).toBeVisible();
  await expect(signalen.locator("li", { hasText: /^Maximale reistijd: 45 min/ })).toBeVisible();
  await expect(signalen.locator("li", { hasText: /^Reistijd naar Werk: 52 min met de auto/ })).toBeVisible();
});

test("a pendelbestemming added to the Koperprofiel is shown as not fetched until Reistijd is fetched again", async ({
  page,
  request,
}) => {
  const school = { label: "School", address: "Kantoorlaan 1, Eindhoven", max_minutes: 60 };
  await request.put("/api/buyer-profile", { data: { ...PROFILE, commute_destinations: [WERK] } });
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await request.put("/api/buyer-profile", { data: { ...PROFILE, commute_destinations: [WERK, school] } });
  await page.goto("/");
  await page.getByRole("button", { name: "Dorpsstraat 41" }).click();

  const reistijd = page.locator("details", { has: page.getByRole("heading", { name: "Reistijd" }) });
  await expect(reistijd.getByText(/Reistijd naar School: nog niet opgehaald/)).toBeVisible();

  await page.getByRole("button", { name: "Reistijd opnieuw ophalen" }).click();
  await expect(reistijd.getByText(/Reistijd naar School: nog niet opgehaald/)).toBeHidden();
  await expect(reistijd.getByText("Reistijd naar School")).toBeVisible();
});
