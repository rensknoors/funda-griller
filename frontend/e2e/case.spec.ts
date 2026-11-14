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
  // 2027 norms (levering after the turn of the year), NHG at 4,40%, label B and the alleenstaandenbonus.
  await expect(page.getByText("€ 461.174")).toBeVisible();
  await expect(page.getByText("+€ 72.928", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("€ 1.461 p/m", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/^Leennormen 2027, levering rond/)).toBeVisible();
  await expect(page.getByText(/hypotheekrente met NHG marktrente 4,4% \(2 november 2026\); zonder NHG marktrente 4,78%/)).toBeVisible();
  await expect(page.getByText(/tegen marktrente 4,4% \(2 november 2026\) met NHG/)).toBeVisible();
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
  await expect(page.getByText("Vraagprijs t.o.v. WOZ", { exact: true })).toBeVisible();
  // 392.000 at peildatum 2025-01-01, in today's prices with the CBS index: 420.289.
  await expect(page.getByText("Vraagprijs t.o.v. WOZ naar vandaag", { exact: true })).toBeVisible();
  await expect(page.getByText(/WOZ €\s420\.289/)).toBeVisible();

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

test("dossier lists its verouderde feiten per bron and refetches that bron", async ({ page }) => {
  await page.route("**/api/listings/80907644/case", async (route) => {
    const caseData = await (await route.fetch()).json();
    for (const fact of caseData.facts) {
      if (fact.source === "woz") Object.assign(fact, { stale: true, ttl_days: 30 });
    }
    await route.fulfill({ json: caseData });
  });
  const refetched: string[] = [];
  await page.route("**/api/listings/80907644/sources/*/refetch", async (route) => {
    refetched.push(new URL(route.request().url()).pathname);
    await route.fallback();
  });
  await page.goto("/");
  await page.getByRole("link", { name: "Buchterweg 15" }).click();

  const block = page.getByRole("region", { name: /feiten? verouderd/ });
  await expect(block.getByRole("link", { name: "WOZ (prijshistorie)" })).toBeVisible();
  await expect(block.getByText("WOZ-waarde 2025")).toBeVisible();
  await expect(block.getByText(/30 dagen geldig/)).toBeVisible();
  await expect(page.locator(".brondekking").getByText("verouderd")).toBeVisible();

  await page.getByRole("link", { name: /feiten? verouderd/ }).click();
  // In-page links scroll; the hash keeps the route.
  await expect(page.locator("#verouderd-title")).toBeInViewport();

  await block.getByRole("button", { name: "WOZ (prijshistorie) bijwerken" }).click();
  await expect.poll(() => refetched).toEqual(["/api/listings/80907644/sources/woz/refetch"]);
  await expect(block).toBeHidden();
});
