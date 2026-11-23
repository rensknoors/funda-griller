import { expect, test } from "@playwright/test";

// A woning of its own in the e2e app (see tests/e2e_app.py). Runs after verdict.spec, whose
// "Dit verandert 1 oordeel" would otherwise count this Oordeel.
const NOTE_URL = "https://www.funda.nl/detail/koop/holtum/huis-kerkpad-6/80907662/";

const PROFILE = {
  household: [{ role: "adult", birth_date: "1988-04-12" }],
  gross_annual_income: 95000,
  assets: { savings: 40000, investments: 15000 },
  current_home: { value: 400000, outstanding_mortgage: 220000, selling_costs: 8000 },
  renovation_tolerance: 3,
};

const NEIGHBOURS = "De buren zeggen dat de fundering van de hele rij is verzakt.";

test("the Notitie is written on the Dossier, read on the Oordeel, and a change makes the Oordeel achterhaald", async ({
  page,
  request,
}) => {
  await request.put("/api/buyer-profile", { data: PROFILE });
  await request.post("/api/listings", { data: { url: NOTE_URL } });
  await page.goto("/#/woning/80907662");
  await expect(page.getByRole("heading", { name: "Dossier: Kerkpad 6" })).toBeVisible();

  const notitie = page.getByRole("region", { name: "Notitie" });
  await notitie.getByRole("textbox", { name: "Notitie" }).fill(NEIGHBOURS);
  await notitie.getByRole("button", { name: "Notitie bewaren" }).click();
  await expect(notitie.getByText("Bewaard")).toBeVisible();

  await page.getByRole("link", { name: "Oordeel", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Oordeel: Kerkpad 6" })).toBeVisible();
  await expect(notitie.getByRole("textbox", { name: "Notitie" })).toHaveValue(NEIGHBOURS);
  await page.getByRole("button", { name: "Oordeel opvragen" }).click();
  await expect(page.getByRole("region", { name: "Oordeel", exact: true })).toBeVisible();
  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie")).toBeHidden();

  // Saving a changed Notitie on the Oordeel makes it achterhaald there and then, without a reload.
  await notitie.getByRole("textbox", { name: "Notitie" }).fill(`${NEIGHBOURS} Herstel kostte bij hen € 80.000.`);
  await notitie.getByRole("button", { name: "Notitie bewaren" }).click();
  await expect(page.getByText("Dit oordeel is gebaseerd op een oudere versie van je notitie.")).toBeVisible();

  await page.reload();
  await expect(notitie.getByRole("textbox", { name: "Notitie" })).toHaveValue(/Herstel kostte bij hen/);
});
