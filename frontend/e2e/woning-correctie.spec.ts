import { expect, test, type Page } from "@playwright/test";

// Woningen of their own in the e2e app. This spec runs after verdict.spec, whose "Dit verandert 1
// oordeel" would otherwise count the Oordeel made here.
const CORRECTION_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-10/80907663/";
// Its advertentie states 128 m² and no perceeloppervlak, and 120 m² on every refetch after.
const RECAPTURE_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-12/80907664/";

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
});

const kenmerk = (page: Page, label: string) =>
  page
    .locator("details", { has: page.getByRole("heading", { name: "Kenmerken" }) })
    .getByRole("listitem")
    .filter({ hasText: label });

test("correcting the woonoppervlak changes the verwachte verkoopprijs and makes the oordeel achterhaald", async ({
  page,
  request,
}) => {
  await request.post("/api/listings", { data: { url: CORRECTION_URL } });
  await request.post("/api/listings/80907663/sources/comparables/refetch");
  await page.goto("/");
  await page.getByRole("link", { name: "Kerkpad 10" }).click();

  // Median € 4.200 per m² of the vergelijkbare woningen plus 4,6% gemiddeld overbod: on 152 m² € 667.766.
  const verwacht = page.getByRole("region", { name: "Verwachte verkoopprijs" });
  await expect(verwacht.getByText("€ 667.766", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();
  await expect(page.getByRole("region", { name: "Oordeel", exact: true }).getByText("Overwegen", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Dossier", exact: true }).click();

  await kenmerk(page, "Woonoppervlak").getByRole("button", { name: "Woonoppervlak (m²) corrigeren" }).click();
  const dialog = page.getByRole("dialog", { name: "Woonoppervlak (m²) corrigeren" });
  await dialog.getByLabel("Woonoppervlak (m²)").fill("112");
  await dialog.getByLabel("Toelichting").fill("NEN 2580-meetrapport");
  await dialog.getByRole("button", { name: "Correctie opslaan" }).click();
  await expect(dialog).toBeHidden();

  // On 112 m²: € 492.038. The fact shows the agent's 152 struck through, with its herkomst and why.
  await expect(verwacht.getByText("€ 492.038", { exact: true })).toBeVisible();
  const row = kenmerk(page, "Woonoppervlak");
  await expect(row.getByText("112", { exact: true })).toBeVisible();
  await expect(row.getByText("gecorrigeerd", { exact: true })).toBeVisible();
  await expect(row.locator("s", { hasText: "152" })).toBeVisible();
  await expect(row.getByText(/Advertentie/)).toBeVisible();
  await expect(row.getByText("NEN 2580-meetrapport")).toBeVisible();
  // The Woning header counts the corrected woonoppervlak too.
  await expect(page.getByText("112 m² wonen")).toBeVisible();

  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie")).toBeVisible();
  await expect(page.getByText("Achterhaald").first()).toBeVisible();

  // Removing the Correctie brings the advertentie's value back.
  await page.getByRole("link", { name: "Dossier", exact: true }).click();
  await kenmerk(page, "Woonoppervlak").getByRole("button", { name: "Woonoppervlak (m²) corrigeren" }).click();
  await expect(dialog.getByLabel("Woonoppervlak (m²)")).toHaveValue("112");
  await expect(dialog.getByLabel("Toelichting")).toHaveValue("NEN 2580-meetrapport");
  await dialog.getByRole("button", { name: "Correctie verwijderen" }).click();
  await expect(dialog).toBeHidden();
  await expect(verwacht.getByText("€ 667.766", { exact: true })).toBeVisible();
  await expect(kenmerk(page, "Woonoppervlak").getByText("gecorrigeerd")).toBeHidden();
});

test("a fact the advertentie leaves out can be filled in, and a changed advertentie says so", async ({
  page,
  request,
}) => {
  await request.post("/api/listings", { data: { url: RECAPTURE_URL } });
  await page.goto("/");
  await page.getByRole("link", { name: "Kerkpad 12" }).click();

  const perceel = kenmerk(page, "Perceeloppervlak");
  await expect(perceel.getByText("onbekend")).toBeVisible();
  await perceel.getByRole("button", { name: "Perceeloppervlak (m²) corrigeren" }).click();
  const perceelDialog = page.getByRole("dialog", { name: "Perceeloppervlak (m²) corrigeren" });
  // Without a Toelichting nothing is saved.
  await perceelDialog.getByLabel("Perceeloppervlak (m²)").fill("240");
  await perceelDialog.getByRole("button", { name: "Correctie opslaan" }).click();
  await expect(perceelDialog.getByText("Schrijf erbij waar de waarde vandaan komt.")).toBeVisible();
  await perceelDialog.getByLabel("Toelichting").fill("Kadaster");
  await perceelDialog.getByRole("button", { name: "Correctie opslaan" }).click();
  await expect(perceelDialog).toBeHidden();
  await expect(perceel.getByText("240", { exact: true })).toBeVisible();
  await expect(perceel.getByText("gecorrigeerd", { exact: true })).toBeVisible();
  await expect(perceel.locator("s", { hasText: "onbekend" })).toBeVisible();

  const wonen = kenmerk(page, "Woonoppervlak");
  await wonen.getByRole("button", { name: "Woonoppervlak (m²) corrigeren" }).click();
  const wonenDialog = page.getByRole("dialog", { name: "Woonoppervlak (m²) corrigeren" });
  await wonenDialog.getByLabel("Woonoppervlak (m²)").fill("112");
  await wonenDialog.getByLabel("Toelichting").fill("zelf nagemeten bij bezichtiging");
  await wonenDialog.getByRole("button", { name: "Correctie opslaan" }).click();
  await expect(wonenDialog).toBeHidden();
  await expect(wonen.getByText("De advertentie noemt nu")).toBeHidden();

  // The refetched advertentie states 120 m²: the Correctie stays, and the fact says the advertentie moved.
  await page.getByRole("button", { name: "Opnieuw ophalen", exact: true }).click();
  await expect(wonen.getByText("De advertentie noemt nu 120 m²")).toBeVisible();
  await expect(wonen.getByText("112", { exact: true })).toBeVisible();
  expect((await request.post("/api/listings/80907664/verdict")).status()).toBe(201);
  await wonen.getByRole("button", { name: "Correctie behouden" }).click();
  await expect(wonen.getByText("De advertentie noemt nu 120 m²")).toBeHidden();
  await expect(wonen.getByText("112", { exact: true })).toBeVisible();
  await expect(wonen.locator("s", { hasText: "120" })).toBeVisible();

  // Keeping an unchanged Correctie changes nothing the Oordeel was built from.
  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await expect(page.getByRole("region", { name: "Oordeel", exact: true })).toBeVisible();
  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie")).toBeHidden();
});
