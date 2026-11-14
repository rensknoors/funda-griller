import { expect, test, type Page } from "@playwright/test";

const LISTING_URL = "https://www.funda.nl/detail/koop/holtum/huis-buchterweg-15/80907644/";
// The e2e backend's fake provider returns this one as available first, sold on refetch.
const CHANGING_URL = "https://www.funda.nl/detail/koop/maastricht/appartement-markt-3/55500001/";

const table = (page: Page) => page.getByRole("table", { name: "Woningen" });
const row = (page: Page, address: string) => table(page).getByRole("row", { name: new RegExp(address) });

/** Fold a row open; its figures sit in the details row it controls. */
async function details(page: Page, address: string) {
  await row(page, address).getByRole("button", { name: "Details tonen" }).click();
  const toggle = row(page, address).getByRole("button", { name: "Details verbergen" });
  return page.locator(`#${await toggle.getAttribute("aria-controls")}`);
}

async function rowOrder(page: Page): Promise<string[]> {
  const names = await table(page).locator("tbody tr").allInnerTexts();
  return names.map((text) => (text.includes("Buchterweg 15") ? "Buchterweg" : text.includes("Markt 3") ? "Markt" : "ander"));
}

test.beforeEach(async ({ request }) => {
  // A deal-breaker the Buchterweg description mentions: a deterministic Harde afwijzing there only.
  await request.put("/api/buyer-profile", {
    data: {
      household: [{ role: "adult", birth_date: "1988-04-12" }],
      gross_annual_income: 95000,
      assets: { savings: 40000, investments: 15000 },
      current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
      deal_breakers: ["Garage"],
      renovation_tolerance: 3,
    },
  });
  // Captured already when another spec ran first; a 409 is fine.
  await request.post("/api/listings", { data: { url: LISTING_URL } });
  await request.post("/api/listings", { data: { url: CHANGING_URL } });
});

test("list compares woningen by oordeel, price and key figures", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Lijst", exact: true }).click();

  const buchterweg = row(page, "Buchterweg 15");
  await expect(buchterweg.getByText("Harde afwijzing")).toBeVisible();
  await expect(buchterweg.getByText("Deal-breaker: Garage")).toBeVisible();
  await expect(buchterweg.getByText("€ 595.000")).toBeVisible();
  await expect(buchterweg.getByText("+41,6%", { exact: true })).toBeHidden();
  const buchterwegDetails = await details(page, "Buchterweg 15");
  await expect(buchterwegDetails.getByText("+41,6%", { exact: true })).toBeVisible();
  await expect(buchterwegDetails.getByText("152 / 410")).toBeVisible();
  await expect(buchterwegDetails.getByText("A", { exact: true })).toBeVisible();
  await expect(row(page, "Markt 3").getByText("Nog geen oordeel")).toBeVisible();

  // Default: tier order, a Harde afwijzing below Woningen without an Oordeel yet.
  expect((await rowOrder(page)).filter((name) => name !== "ander")).toEqual(["Markt", "Buchterweg"]);

  const priceHeader = table(page).getByRole("columnheader", { name: /Vraagprijs/ });
  await priceHeader.getByRole("button").click();
  await expect(priceHeader).toHaveAttribute("aria-sort", "ascending");
  await priceHeader.getByRole("button").click();
  await expect(priceHeader).toHaveAttribute("aria-sort", "descending");
  expect((await rowOrder(page)).filter((name) => name !== "ander")).toEqual(["Buchterweg", "Markt"]);

  await page.getByLabel("Vraagprijs tot").fill("500000");
  await expect(row(page, "Buchterweg 15")).toBeHidden();
  await expect(row(page, "Markt 3")).toBeVisible();
  await page.getByLabel("Vraagprijs tot").fill("");

  await page.getByRole("checkbox", { name: /Harde afwijzing/ }).check();
  await expect(row(page, "Markt 3")).toBeHidden();
  await expect(row(page, "Buchterweg 15")).toBeVisible();
});

test("woningen with verouderde gegevens stand out and can be filtered", async ({ page }) => {
  await page.route("**/api/listings?*", async (route) => {
    const listings = await (await route.fetch()).json();
    for (const listing of listings) {
      if (listing.funda_id === "80907644") listing.comparison.stale_count = 3;
    }
    await route.fulfill({ json: listings });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Lijst", exact: true }).click();

  await expect(row(page, "Buchterweg 15").getByText("3 verouderd")).toBeVisible();
  await page.getByRole("checkbox", { name: "Met verouderde feiten" }).check();
  await expect(row(page, "Markt 3")).toBeHidden();
  await expect(row(page, "Buchterweg 15")).toBeVisible();
});

test("refetch shows a status change; archive and restore keep the woning", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Lijst", exact: true }).click();

  await row(page, "Markt 3").getByRole("button", { name: "Acties", exact: true }).click();
  await page.getByRole("menuitem", { name: "Opnieuw ophalen" }).click();
  const markt = row(page, "Markt 3");
  await expect(markt.getByText("Verkocht")).toBeVisible();
  await expect(markt.getByText("was Beschikbaar")).toBeVisible();

  await markt.getByRole("button", { name: "Acties", exact: true }).click();
  await page.getByRole("menuitem", { name: "Archiveren" }).click();
  const dialog = page.getByRole("dialog", { name: "Markt 3 archiveren?" });
  await expect(dialog.getByText(/momentopnamen en dossier blijven bewaard/)).toBeVisible();
  await dialog.getByRole("button", { name: "Archiveren" }).click();
  await expect(row(page, "Markt 3")).toBeHidden();

  await page.getByRole("button", { name: "1 gearchiveerd" }).click();
  await expect(row(page, "Markt 3").getByText("Gearchiveerd")).toBeVisible();
  await row(page, "Markt 3").getByRole("button", { name: "Acties", exact: true }).click();
  await page.getByRole("menuitem", { name: "Terugzetten" }).click();
  await expect(row(page, "Markt 3").getByText("Gearchiveerd")).toBeHidden();
  await page.getByRole("button", { name: "Verberg gearchiveerd" }).click();
  await expect(row(page, "Markt 3")).toBeVisible();
  await expect(row(page, "Markt 3").getByText("Verkocht")).toBeVisible();
});

test("woningen show as photo cards by default, with the oordeel, price and key figures", async ({ page }) => {
  await page.goto("/");

  const cards = page.getByRole("list", { name: "Woningen" });
  const buchterweg = cards.getByRole("listitem", { name: "Buchterweg 15" });
  await expect(buchterweg.getByText("Harde afwijzing")).toBeVisible();
  await expect(buchterweg.getByText("€ 595.000")).toBeVisible();
  await expect(buchterweg.getByText("Deal-breaker: Garage")).toBeVisible();
  await expect(buchterweg.getByText("WOZ +41,6%")).toBeVisible();
  await expect(buchterweg.locator("img")).toHaveAttribute("src", /\/api\/listings\/80907644\/photos\//);

  // The choice of view is remembered.
  await page.getByRole("button", { name: "Lijst", exact: true }).click();
  await page.reload();
  await expect(page.getByRole("table", { name: "Woningen" })).toBeVisible();
  await page.getByRole("button", { name: "Kaarten", exact: true }).click();

  await buchterweg.getByRole("link", { name: "Buchterweg 15" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Buchterweg 15" })).toBeVisible();
  const facts = page.locator(".woning-head .woning-facts");
  await expect(facts.getByText("152 m² wonen")).toBeVisible();
  await expect(facts.getByText("410 m² perceel")).toBeVisible();
  await expect(facts.getByText("Energielabel A")).toBeVisible();

  await page.getByRole("button", { name: "Foto 1 openen" }).click();
  const viewer = page.getByRole("dialog", { name: "Foto 1" });
  await viewer.getByRole("button", { name: "Volgende foto" }).click();
  await expect(page.getByRole("dialog", { name: "Foto 2" })).toBeVisible();
  await page.getByRole("dialog", { name: "Foto 2" }).getByRole("button", { name: "Sluiten" }).click();

  // A thumbnail in the mosaic opens the viewer at its own photo.
  await page.getByRole("button", { name: "Foto 2 openen" }).click();
  await expect(page.getByRole("dialog", { name: "Foto 2" })).toBeVisible();
});
