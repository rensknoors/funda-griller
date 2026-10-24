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
  await page.getByRole("button", { name: "Buchterweg 15" }).click();

  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();
  await expect(page.getByText("Maximale hypotheek", { exact: true })).toBeVisible();
  await expect(page.getByText("€ 486.660")).toBeVisible();
  await expect(page.getByText("▲ +€ 98.784").first()).toBeVisible();
  await expect(page.getByText(/^Regels 2026/)).toBeVisible();
  await expect(page.getByText("Vraagprijs", { exact: true }).first()).toBeVisible();
  await expect(page.getByLabel(/Bron: advertentie/).first()).toBeVisible();
});
