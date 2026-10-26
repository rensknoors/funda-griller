import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

test("dossier shows listing facts with herkomst and the affordability for the saved koperprofiel", async ({
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
  await page.goto("/");
  await page.getByLabel("Funda-link").fill(LISTING_URL);
  await page.getByRole("button", { name: "Ophalen" }).click();
  await page.getByRole("link", { name: "Buchterweg 15" }).click();

  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();
  await expect(page.getByText("Maximale hypotheek", { exact: true })).toBeVisible();
  await expect(page.getByText("€ 496.660")).toBeVisible();
  await expect(page.getByText("+€ 109.519", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/^Regels 2026/)).toBeVisible();
  await expect(page.getByText("Vraagprijs", { exact: true }).first()).toBeVisible();
  await expect(page.getByLabel(/Bron: advertentie/).first()).toBeVisible();
});

test("dossier shows bronnen: official energielabel, third-party WOZ, coverage and per-bron refetch", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Buchterweg 15" }).click();

  await expect(page.getByText(/6 bronnen: 3 gelukt, 0 mislukt, 3 overgeslagen/)).toBeVisible();
  await expect(page.getByLabel(/Bron: Energielabelregister, opgehaald/)).toBeVisible();
  await expect(page.getByText("Nee: advertentie B, register A")).toBeVisible();
  await expect(page.getByText("WOZ-waarde 2025")).toBeVisible();
  await expect(page.getByLabel(/Bron: WOZ \(prijshistorie\), onofficieel/).first()).toBeVisible();
  await expect(page.getByText("Vraagprijs t.o.v. WOZ")).toBeVisible();

  await page.getByRole("button", { name: "WOZ (prijshistorie) opnieuw ophalen" }).click();
  await expect(page.getByText("WOZ-waarde 2024")).toBeVisible();
});

test("dossier shows flood and soil risk under omgeving, its risico signaal, and skipped geluid", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Buchterweg 15" }).click();

  const omgeving = page.locator("details", { has: page.getByRole("heading", { name: "Omgeving" }) });
  await expect(omgeving.getByText("Waterdiepte bij overstroming (kleine kans)")).toBeVisible();
  await expect(omgeving.getByText("0,88 m")).toBeVisible();
  await expect(omgeving.getByText("1,5 mm per jaar")).toBeVisible();
  await expect(omgeving.getByLabel(/Bron: Overstroming en bodem, opgehaald/).first()).toBeVisible();
  await expect(omgeving.getByText("Bron overgeslagen, geen gegevens van Geluid.")).toBeVisible();
  await expect(page.getByText(/Geluid: overgeslagen \(geen coördinaten\)/)).toBeVisible();

  const signalen = page.getByRole("region", { name: "Signalen" });
  await expect(signalen.getByRole("heading", { name: /Risico \(1\)/ })).toBeVisible();
  await expect(signalen.getByText(/Overstromingsrisico: meer dan 0,5 m water/)).toBeVisible();

  await page.getByRole("button", { name: "Overstroming en bodem opnieuw ophalen" }).click();
  await expect(omgeving.getByText("0,88 m")).toBeVisible();
});
