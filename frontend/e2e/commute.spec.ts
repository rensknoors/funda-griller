import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-41/80907651/";

test("dossier shows the reistijd per pendelbestemming and a minpunt when it is too far", async ({
  page,
  request,
}) => {
  await request.put("/api/buyer-profile", {
    data: {
      household: [{ role: "adult", birth_date: "1988-04-12" }],
      gross_annual_income: 95000,
      assets: { savings: 40000, investments: 15000 },
      commute_destinations: [{ label: "Werk", address: "Kantoorlaan 1, Eindhoven", max_minutes: 45 }],
      renovation_tolerance: 3,
    },
  });
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await page.goto("/");
  await page.getByRole("button", { name: "Dorpsstraat 41" }).click();

  await expect(page.getByText(/Reistijd: gelukt/)).toBeVisible();
  const reistijd = page.locator("details", { has: page.getByRole("heading", { name: "Reistijd" }) });
  await expect(reistijd.getByText("Reistijd naar Werk")).toBeVisible();
  await expect(
    reistijd.getByText("52 min met de auto (fiets 140 min), openbaar vervoer niet meegerekend"),
  ).toBeVisible();
  await expect(reistijd.getByLabel(/Bron: Reistijd, onofficieel, opgehaald/)).toBeVisible();

  const signalen = page.getByRole("region", { name: "Signalen" });
  await signalen.getByText("Reistijd boven je maximum: Werk").click();
  await expect(signalen.getByText("Regel commute_too_long · versie 1")).toBeVisible();
  await expect(signalen.getByText("Maximale reistijd:")).toBeVisible();
  await expect(signalen.getByText("45 min", { exact: true })).toBeVisible();
});
