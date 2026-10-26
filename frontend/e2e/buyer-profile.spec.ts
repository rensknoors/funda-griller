import { type Page, expect, test } from "@playwright/test";

const PROFILE = "**/api/buyer-profile";

/** Pretend no Koperprofiel has been saved yet, whatever earlier specs stored. */
async function firstRun(page: Page) {
  await page.route(PROFILE, (route) =>
    route.request().method() === "GET" ? route.fulfill({ status: 404, json: { detail: "Nog geen koperprofiel" } }) : route.fallback(),
  );
}

async function openSection(page: Page, name: string) {
  await page.getByRole("navigation", { name: "Onderdelen" }).getByRole("link", { name }).click();
}

test("first run opens Huishouden only, with one-line hints and the Gevolgen hint", async ({ page }) => {
  await firstRun(page);
  await page.goto("/#/koperprofiel");

  await expect(page.getByLabel("Geboortedatum lid 1")).toBeVisible();
  await expect(page.getByLabel("Bruto jaarinkomen huishouden (€)")).toBeHidden();
  await expect(page.getByText("Bruto jaarinkomen van het huishouden.")).toBeVisible();
  await expect(page.getByText("Vul inkomen in om je budget te zien")).toBeVisible();

  await openSection(page, "Inkomen");

  await expect(page.getByLabel("Bruto jaarinkomen huishouden (€)")).toBeFocused();
});

test("Gevolgen panel follows the vakken live, with the rules year", async ({ page }) => {
  await firstRun(page);
  await page.goto("/#/koperprofiel");
  await openSection(page, "Inkomen");
  await page.getByLabel("Bruto jaarinkomen huishouden (€)").fill("95000");

  const gevolgen = page.getByRole("complementary", { name: "Gevolgen" });
  await expect(gevolgen.getByText("€ 486.660")).toBeVisible();
  await expect(gevolgen.getByText("€ 472.166")).toBeVisible();
  await expect(gevolgen.getByText(/^Regels 2026/)).toBeVisible();

  await openSection(page, "Vermogen en eigen woning");
  await page.getByLabel("Spaargeld (€)").fill("40000");
  await page.getByLabel("Ik heb een eigen woning").check();
  await page.getByLabel("Woningwaarde (€)").fill("400000");
  await page.getByLabel("Openstaande hypotheek (€)").fill("220000");
  await page.getByLabel("Verkoopkosten (€)").fill("8000");

  await expect(gevolgen.getByText("€ 172.000")).toBeVisible();
  await expect(gevolgen.getByText("€ 680.009")).toBeVisible();
});

test("a vak is checked on blur; save stays disabled until it is fixed", async ({ page }) => {
  await firstRun(page);
  await page.goto("/#/koperprofiel");
  await openSection(page, "Inkomen");
  const income = page.getByLabel("Bruto jaarinkomen huishouden (€)");

  await income.fill("-5");
  await income.press("Tab");

  await expect(page.getByText("Bedrag buiten bereik")).toBeVisible();
  await expect(income).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByRole("button", { name: "Opslaan" })).toBeDisabled();
  await expect(page.getByText("1 vak is niet correct ingevuld")).toBeVisible();

  await page.getByRole("link", { name: "Naar het eerste probleem" }).click();
  await expect(income).toBeFocused();

  await income.fill("95000");

  await expect(page.getByText("Bedrag buiten bereik")).toBeHidden();
  await expect(page.getByRole("button", { name: "Opslaan" })).toBeEnabled();
});

test("wensen can be reordered with the keyboard", async ({ page }) => {
  await firstRun(page);
  await page.goto("/#/koperprofiel");
  await openSection(page, "Wensen");
  await page.getByRole("button", { name: "Must-have toevoegen" }).click();
  await page.getByLabel("Must-have 1", { exact: true }).fill("tuin");
  await page.getByRole("button", { name: "Must-have toevoegen" }).click();
  await page.getByLabel("Must-have 2", { exact: true }).fill("garage");

  await page.getByLabel("Must-have 2", { exact: true }).press("Alt+ArrowUp");

  await expect(page.getByLabel("Must-have 1", { exact: true })).toHaveValue("garage");
  await expect(page.getByLabel("Must-have 1", { exact: true })).toBeFocused();

  await page.getByRole("button", { name: "Must-have 1 omlaag" }).click();

  await expect(page.getByLabel("Must-have 1", { exact: true })).toHaveValue("tuin");
  await expect(page.getByText(/gaat mee naar het taalmodel/).first()).toBeVisible();
});

test("loading shows a skeleton; a load failure offers Opnieuw proberen", async ({ page }) => {
  let fail = true;
  await page.route(PROFILE, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, 300));
    return fail ? route.fulfill({ status: 500, body: "boom" }) : route.fulfill({ status: 404, json: {} });
  });
  await page.goto("/#/koperprofiel");

  await expect(page.getByText("Koperprofiel laden")).toBeAttached();
  await expect(page.getByRole("alert").filter({ hasText: "Koperprofiel laden mislukt" })).toBeVisible();

  fail = false;
  await page.getByRole("button", { name: "Opnieuw proberen" }).click();

  await expect(page.getByLabel("Geboortedatum lid 1")).toBeVisible();
});

test("a failed save keeps the input and can be retried", async ({ page }) => {
  await firstRun(page);
  let failSave = true;
  await page.route(PROFILE, (route) =>
    route.request().method() === "PUT" && failSave ? route.fulfill({ status: 500, body: "boom" }) : route.fallback(),
  );
  await page.goto("/#/koperprofiel");
  await fillValidProfile(page);

  await page.getByRole("button", { name: "Opslaan" }).click();

  await expect(page.getByRole("alert").filter({ hasText: "Opslaan mislukt" })).toBeVisible();
  await expect(page.getByLabel("Bruto jaarinkomen huishouden (€)")).toHaveValue("95000");

  failSave = false;
  await page.getByRole("button", { name: "Opnieuw proberen" }).click();

  await expect(page.getByText(/Opgeslagen als versie \d+\./)).toBeVisible();
});

test("koperprofiel is saved and reloaded with every section open", async ({ page }) => {
  await page.goto("/#/koperprofiel");
  await fillValidProfile(page);
  await page.getByRole("button", { name: "Must-have toevoegen" }).click();
  await page.getByLabel("Must-have 1", { exact: true }).fill("tuin");

  await page.getByRole("button", { name: "Opslaan" }).click();
  await expect(page.getByText(/Opgeslagen als versie \d+\./)).toBeVisible();

  await page.reload();

  await expect(page.getByLabel("Bruto jaarinkomen huishouden (€)")).toHaveValue("95000");
  await expect(page.getByLabel("Must-have 1", { exact: true })).toHaveValue("tuin");
  await expect(page.getByText("Opgeslagen op dit apparaat, nooit geüpload.")).toBeVisible();
});

test("on a narrow screen the section index is a select", async ({ page }) => {
  await page.setViewportSize({ width: 600, height: 900 });
  await firstRun(page);
  await page.goto("/#/koperprofiel");

  await expect(page.getByRole("navigation", { name: "Onderdelen" })).toBeHidden();
  await page.getByLabel("Ga naar onderdeel").selectOption("wensen");

  await expect(page.getByRole("button", { name: "Must-have toevoegen" })).toBeVisible();
});

test("the form is set in self-hosted Archivo", async ({ page }) => {
  await firstRun(page);
  await page.goto("/#/koperprofiel");

  const loaded = await page.evaluate(async () => {
    await document.fonts.ready;
    return [...document.fonts].some((face) => face.family.includes("Archivo") && face.status === "loaded");
  });

  expect(loaded).toBe(true);
});

/** Fills every required vak with valid values, opening sections as it goes. */
async function fillValidProfile(page: Page) {
  await openSection(page, "Huishouden");
  await page.getByLabel("Geboortedatum lid 1").fill("1988-04-12");
  await openSection(page, "Inkomen");
  await page.getByLabel("Bruto jaarinkomen huishouden (€)").fill("95000");
  await openSection(page, "Vermogen en eigen woning");
  await page.getByLabel("Spaargeld (€)").fill("40000");
  await page.getByLabel("Beleggingen (€)").fill("0");
  await openSection(page, "Reizen en verbouwen");
  await page.getByRole("radio", { name: /Gemiddeld/ }).check();
  await openSection(page, "Wensen");
}
