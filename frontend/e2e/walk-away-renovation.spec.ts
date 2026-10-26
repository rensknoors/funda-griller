import { expect, test } from "@playwright/test";
import path from "node:path";

// A woning of its own in the e2e app, so the Direct nodig item from its Vragenlijst moves no other
// spec's figures. Specs run in file order; this one runs after verdict.spec, whose "Dit verandert 1
// oordeel" would otherwise count this spec's Oordeel.
const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-42/80907652/";
const VRAGENLIJST = path.join(import.meta.dirname, "fixtures", "Vragenlijst.pdf");

test("verbouwingskosten by urgency, geschat with evidence, subtracted in the biedadvies", async ({
  page,
  request,
}) => {
  await request.put("/api/buyer-profile", {
    data: {
      household: [{ role: "adult", birth_date: "1988-04-12" }],
      gross_annual_income: 95000,
      assets: { savings: 40000, investments: 15000 },
      current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
      renovation_tolerance: 3,
    },
  });
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await page.goto("/");
  await page.getByRole("link", { name: "Dorpsstraat 42" }).click();

  const group = page.locator("details", { has: page.getByRole("heading", { name: "Verbouwingskosten" }) });
  // Built in 1931 with a fair roof in the photos: Binnen 5 jaar only, and no Vragenlijst yet.
  await expect(group.getByText(/Niet meegenomen: geen Vragenlijst/)).toBeVisible();
  await expect(group.getByRole("heading", { name: /Binnen 5 jaar/ })).toBeVisible();
  await expect(group.getByText(/Asbestinventarisatie/)).toBeVisible();
  await expect(group.getByText(/onderzoek op basis van bouwjaar/)).toBeVisible();
  await expect(group.getByRole("heading", { name: /Direct nodig/ })).toHaveCount(0);

  await page.getByRole("region", { name: "Documenten" }).getByLabel("Document uploaden").setInputFiles(VRAGENLIJST);

  // The seller states asbestos: removal is Direct nodig and replaces the survey.
  const direct = group.locator(".urgency-direct");
  await expect(direct.getByRole("heading", { name: "Direct nodig: € 2.000 – € 10.000" })).toBeVisible();
  await expect(group.getByText(/Asbestinventarisatie/)).toHaveCount(0);
  await expect(group.getByText(/Niet meegenomen/)).toHaveCount(0);
  await direct.getByText("Asbest laten verwijderen").click();
  await expect(direct.getByText("Geschat · prijspeil 2025")).toBeVisible();
  await expect(direct.getByText("“Asbest in de dakplaten van de schuur.”")).toBeVisible();
  await expect(direct.getByRole("link", { name: "Zie verkoper-informatie" })).toBeVisible();

  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();
  const advies = page.getByRole("region", { name: "Biedadvies" });
  await advies.getByText("Hoe berekend").click();
  await expect(advies.getByText(/na aftrek van €\s6\.000 Direct nodig onderhoud/)).toBeVisible();
  // (595.000 − 6.000) × 1,05
  await expect(advies.getByText("Vraagprijs € 595.000 − € 6.000 Direct nodig + 5%: € 618.450")).toBeVisible();

  await page.getByRole("link", { name: "Dossier", exact: true }).click();
  await page.getByRole("link", { name: "Terug naar woningen" }).click();
  const row = page.getByRole("table", { name: "Woningen" }).getByRole("row", { name: /Dorpsstraat 42/ });
  await expect(row.getByText("€ 2.000 – € 10.000")).toBeVisible();
});
