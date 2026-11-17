import { expect, test } from "@playwright/test";

// Woningen of their own in the e2e app, so the Oordeel made here leaves the other specs alone; this
// spec runs after verdict.spec, whose "Dit verandert 1 oordeel" would otherwise count it.
// Hoogstraat 7 has no WOZ-waarde (no Expected Sale Price), Hoogstraat 9 a much lower one.
const NO_WOZ_URL = "https://www.funda.nl/detail/koop/holtum/huis-hoogstraat-7/80907657/";
const LOW_WOZ_URL = "https://www.funda.nl/detail/koop/holtum/huis-hoogstraat-9/80907659/";
const BUCHTERWEG_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";

test.beforeEach(async ({ request }) => {
  await request.put("/api/buyer-profile", {
    data: {
      household: [{ role: "adult", birth_date: "1988-04-12" }],
      gross_annual_income: 95000,
      assets: { savings: 40000, investments: 15000 },
      current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
      renovation_tolerance: 3,
    },
  });
  // Captured already when an earlier test ran; a 409 is fine.
  await request.post("/api/listings", { data: { url: NO_WOZ_URL } });
  await request.post("/api/listings", { data: { url: LOW_WOZ_URL } });
  await request.post("/api/listings", { data: { url: BUCHTERWEG_URL } });
});

test("the list sorts by headroom at the verwachte verkoopprijs and asks for comparables when there is none", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Lijst", exact: true }).click();
  await page.getByLabel("Sorteren").selectOption("headroom:descending");

  const rows = page.getByRole("table", { name: "Woningen" }).locator("tbody tr");
  const order = async () =>
    (await rows.allInnerTexts())
      .map((text) => ["Hoogstraat 9", "Buchterweg 15", "Hoogstraat 7"].find((address) => text.includes(address)))
      .filter(Boolean);
  // 300.000 and 392.000 WOZ in today's prices (321.5k and 420.3k) leave 98k more room on Hoogstraat 9;
  // Hoogstraat 7 has no verwachte verkoopprijs, so no headroom, and sorts last.
  await expect.poll(order).toEqual(["Hoogstraat 9", "Buchterweg 15", "Hoogstraat 7"]);

  const open = async (address: string) => {
    const row = page.getByRole("row", { name: new RegExp(address) });
    await row.getByRole("button", { name: "Details tonen" }).click();
    return page.locator(`#${await row.getByRole("button", { name: "Details verbergen" }).getAttribute("aria-controls")}`);
  };
  const buchterweg = await open("Buchterweg 15");
  await expect(buchterweg.getByText("Ruimte boven verwachte prijs")).toBeVisible();
  await expect(buchterweg.getByText("Haal vergelijkbare woningen op")).toBeHidden();
  const hoogstraat7 = await open("Hoogstraat 7");
  await expect(hoogstraat7.getByText("Ruimte boven verwachte prijs")).toBeVisible();
  await expect(hoogstraat7.getByText("Haal vergelijkbare woningen op")).toBeVisible();

  await page.getByRole("button", { name: "Kaarten", exact: true }).click();
  const card = page.getByRole("listitem", { name: "Hoogstraat 7" });
  await expect(card.getByText("– Haal vergelijkbare woningen op")).toBeVisible();
  await expect(page.getByRole("listitem", { name: "Buchterweg 15" }).getByText(/ruimte$/)).toBeVisible();
});

test("without a verwachte verkoopprijs the dossier says so and the biedadvies holds only the voorwaarden", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Hoogstraat 7" }).click();

  const block = page.getByRole("region", { name: "Verwachte verkoopprijs" });
  await expect(block.getByText(/Te weinig gegevens om de prijs te beoordelen/)).toBeVisible();
  await expect(block.getByRole("link", { name: "Haal vergelijkbare woningen op" })).toBeVisible();

  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();

  const advies = page.getByRole("region", { name: "Biedadvies" });
  await expect(advies.getByText("Haal vergelijkbare woningen op voor een Maximumbod.")).toBeVisible();
  await expect(advies.getByText("Bouwkundige keuring")).toBeVisible();
  await expect(advies.getByText("Openingsbod")).toBeHidden();
  await expect(advies.getByText(/Maandlasten bij/)).toBeHidden();
});
