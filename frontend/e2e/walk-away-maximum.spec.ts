import { expect, test } from "@playwright/test";

// A woning of its own in the e2e app. Specs share one backend and run in file order; this one runs
// after verdict.spec, whose "Dit verandert 1 oordeel" would otherwise count this spec's Oordeel.
const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-dorpsstraat-40/80907650/";

test("vergelijkbare woningen are fetched on request and ground the Maximumbod", async ({ page, request }) => {
  await request.post("/api/listings", { data: { url: LISTING_URL } });
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
  await page.getByRole("button", { name: "Dorpsstraat 40" }).click();

  const group = page.locator("details", { has: page.getByRole("heading", { name: "Vergelijkbare woningen" }) });
  await expect(group.getByText("Nog niet opgehaald")).toBeVisible();
  await group.getByRole("button", { name: "Vergelijkbare woningen ophalen" }).click();

  // Per m² 4000, 4200 and 4400: median 4200, so 152 m² is € 638.400 by comparables.
  await expect(group.getByText("3 vergelijkbare woningen")).toBeVisible();
  await expect(group.getByRole("link", { name: "Kerkstraat 8" })).toBeVisible();
  await expect(group.getByText("Vraagprijs per m² t.o.v. vergelijkbaar")).toBeVisible();
  await expect(group.getByText(/-6,8%/)).toBeVisible();
  await expect(group.getByText(/^€\s638\.400$/)).toBeVisible();
  await expect(page.getByLabel("Kerncijfers").getByText("-6,8%")).toBeVisible();

  await page.getByRole("button", { name: "Oordeel bekijken" }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();
  const advies = page.getByRole("region", { name: "Biedadvies" });
  await advies.getByText("Hoe berekend").click();
  await expect(advies.getByText(/Vergelijkbare woningen €\s638\.400 \+ 10%: €\s702\.240/)).toBeVisible();
  await expect(advies.getByText(/Zwak onderbouwd/)).toBeHidden();

  await page.getByRole("button", { name: "Terug naar dossier" }).click();
  await page.getByRole("button", { name: "Terug naar woningen" }).click();
  const row = page.getByRole("table", { name: "Woningen" }).getByRole("row", { name: /Dorpsstraat 40/ });
  await expect(row.getByText(/▼ \D?6,8%/)).toBeVisible();
});
