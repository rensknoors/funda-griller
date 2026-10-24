import { expect, test } from "@playwright/test";

// The e2e backend's fake provider reports this listing as blocked.
const BLOCKED_URL = "https://www.funda.nl/detail/koop/utrecht/huis-oudegracht-2/12345678/";

test("blocked fetch offers manual entry, and the entered woning opens as a dossier", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Funda-link").fill(BLOCKED_URL);
  await page.getByRole("button", { name: "Ophalen", exact: true }).click();

  await expect(page.getByText(/aanbieder geblokkeerd/)).toBeVisible();
  await page.getByRole("button", { name: "Handmatig invoeren" }).click();

  const form = page.getByRole("form", { name: "Woning handmatig invoeren" });
  await expect(form.getByLabel("Funda-link")).toHaveValue(BLOCKED_URL);
  await form.getByLabel("Status").selectOption("Beschikbaar");
  await form.getByLabel("Adres").fill("Oudegracht 2");
  await form.getByLabel("Plaats").fill("Utrecht");
  await form.getByLabel("Vraagprijs (€)").fill("425000");
  await form.getByLabel("Woonoppervlak (m²)").fill("96");
  await form.getByLabel("Foto's").setInputFiles({
    name: "voorgevel.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("jpeg"),
  });
  await form.getByRole("button", { name: "Woning opslaan" }).click();

  await expect(form).toBeHidden();
  const row = page.getByRole("row", { name: /Oudegracht 2/ });
  await expect(row.getByText("Handmatig ingevoerd")).toBeVisible();
  await expect(row.getByText("€ 425.000")).toBeVisible();

  await page.getByRole("button", { name: "Oudegracht 2" }).click();
  await expect(page.getByRole("heading", { name: "Dossier: Oudegracht 2" })).toBeVisible();
  await expect(page.getByText("Handmatig ingevoerd")).toBeVisible();
});
