import { expect, test } from "@playwright/test";

test("koperprofiel can be filled in, rejected when invalid, saved and reloaded", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("Geboortedatum lid 1").fill("1988-04-12");
  await page.getByLabel("Bruto jaarinkomen huishouden (€)").fill("-5");
  await page.getByLabel("Spaargeld (€)").fill("40000");
  await page.getByLabel("Beleggingen (€)").fill("0");
  await page.getByRole("radio", { name: /Gemiddeld/ }).check();
  await page.getByRole("button", { name: "Must-have toevoegen" }).click();
  await page.getByLabel("Must-have 1", { exact: true }).fill("tuin");
  await page.getByRole("button", { name: "Opslaan" }).click();

  await expect(page.getByText("Bedrag buiten bereik")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("1 vak is niet correct ingevuld");

  await page.getByLabel("Bruto jaarinkomen huishouden (€)").fill("95000");
  await page.getByRole("button", { name: "Opslaan" }).click();

  await expect(page.getByText(/Opgeslagen als versie \d+\./)).toBeVisible();

  await page.reload();

  await expect(page.getByLabel("Bruto jaarinkomen huishouden (€)")).toHaveValue("95000");
  await expect(page.getByLabel("Must-have 1", { exact: true })).toHaveValue("tuin");
  await expect(page.getByText("Opgeslagen op dit apparaat, nooit geüpload.")).toBeVisible();
});
