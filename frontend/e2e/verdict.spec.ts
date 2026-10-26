import { expect, test } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

const PROFILE = {
  household: [{ role: "adult", birth_date: "1988-04-12" }],
  gross_annual_income: 95000,
  assets: { savings: 40000, investments: 15000 },
  current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
  renovation_tolerance: 3,
};

test("profile, URL, dossier and oordeel with biedadvies; a profile edit makes it achterhaald", async ({
  page,
  request,
}) => {
  await request.put("/api/buyer-profile", { data: PROFILE });
  await page.goto("/");
  await page.getByLabel("Funda-link").fill(LISTING_URL);
  await page.getByRole("button", { name: "Ophalen", exact: true }).click();
  await page.getByRole("button", { name: "Buchterweg 15" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();

  await page.getByRole("button", { name: "Oordeel bekijken" }).click();
  await expect(page.getByRole("heading", { name: "Oordeel: Buchterweg 15" })).toBeVisible();
  await expect(page.getByText("Nog geen oordeel")).toBeVisible();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();

  const tier = page.getByRole("region", { name: "Oordeel", exact: true });
  await expect(tier.getByText("Overwegen", { exact: true })).toBeVisible();
  const advies = page.getByRole("region", { name: "Biedadvies" });
  await expect(advies.getByText("Openingsbod")).toBeVisible();
  await expect(advies.getByText("€ 580.000")).toBeVisible();
  // No vergelijkbare woningen fetched: the Maximumbod is the vraagprijs plus 5%, and says it is weak.
  await expect(advies.getByText("€ 624.750", { exact: true })).toBeVisible();
  await expect(advies.getByText(/Zwak onderbouwd: te weinig vergelijkbare woningen/)).toBeVisible();
  await expect(advies.getByText("Bouwkundige keuring")).toBeVisible();
  await advies.getByText("Hoe berekend").click();
  await expect(advies.getByText("Betaalruimte: tot € 704.519")).toBeVisible();
  await expect(advies.getByText("Vraagprijs € 595.000 + 5%: € 624.750")).toBeVisible();
  const redenering = page.getByRole("region", { name: "Redenering" });
  await expect(redenering.getByRole("button", { name: /Vraagprijs ver boven de WOZ-waarde/ })).toBeVisible();
  await expect(page.getByText(/Koperprofiel versie \d+/).first()).toBeVisible();

  await request.put("/api/buyer-profile", { data: { ...PROFILE, renovation_tolerance: 2 } });
  await page.getByRole("button", { name: "Terug naar dossier" }).click();
  await page.getByRole("button", { name: "Oordeel bekijken" }).click();

  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie")).toBeVisible();
  await expect(page.getByText("Achterhaald").first()).toBeVisible();
  await page.getByRole("button", { name: "Oordeel opnieuw draaien" }).click();
  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie")).toBeHidden();
  await expect(page.getByText("Eerdere oordelen (1)")).toBeVisible();

  await redenering.getByRole("button", { name: /Vraagprijs ver boven de WOZ-waarde/ }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();

  // The list shows the Oordeel tier; saving the koperprofiel says how many Oordelen it changes.
  await page.getByRole("button", { name: "Terug naar woningen" }).click();
  const row = page.getByRole("table", { name: "Woningen" }).getByRole("row", { name: /Buchterweg 15/ });
  await expect(row.getByText("Overwegen")).toBeVisible();
  await page.getByRole("button", { name: "Opslaan" }).click();
  await expect(page.getByText("Dit verandert 1 oordeel.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Naar de woningen" })).toHaveAttribute("href", "#woningen");

  await row.getByRole("button", { name: "Acties" }).click();
  await page.getByRole("menuitem", { name: "Oordeel opnieuw draaien" }).click();
  await row.getByRole("button", { name: "Buchterweg 15" }).click();
  await page.getByRole("button", { name: "Oordeel bekijken" }).click();
  await expect(page.getByText("Eerdere oordelen (2)")).toBeVisible();
  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie")).toBeHidden();
});

test("a model failure shows the backend's reason, such as a missing API key", async ({ page, request }) => {
  await request.put("/api/buyer-profile", { data: PROFILE });
  await page.route("**/api/listings/80907644/verdict", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 502, json: { code: "llm_unavailable", reason: "no Gemini API key configured" } })
      : route.fallback(),
  );
  await page.goto("/");
  await page.getByLabel("Funda-link").fill(LISTING_URL);
  await page.getByRole("button", { name: "Ophalen", exact: true }).click();
  await page.getByRole("button", { name: "Buchterweg 15" }).click();
  await page.getByRole("button", { name: "Oordeel bekijken" }).click();
  await page.getByRole("button", { name: /^Oordeel (opvragen|opnieuw draaien)$/ }).first().click();

  await expect(page.getByRole("alert")).toContainText("no Gemini API key configured");
});
