import { expect, test } from "@playwright/test";

// A backend that accepts connections but never answers must not freeze the page.
test("a hung API ends in error states instead of endless loading", async ({ page }) => {
  test.setTimeout(30_000);
  for (const path of ["**/api/health", "**/api/listings?*", "**/api/buyer-profile"]) {
    await page.route(path, () => undefined); // never fulfilled
  }
  await page.goto("/");

  await expect(page.getByRole("status").filter({ hasText: "API:" })).toHaveText("API: unreachable", {
    timeout: 15_000,
  });
  await expect(page.getByText("Woningen laden mislukt.")).toBeVisible();
  await page.getByRole("navigation", { name: "Hoofdmenu" }).getByRole("link", { name: "Koperprofiel" }).click();
  await expect(page.getByText("Koperprofiel laden mislukt.")).toBeVisible({ timeout: 15_000 });
});

test("a capture with no answer says the server is not responding and frees Ophalen", async ({ page }) => {
  await page.route("**/api/listings", (route) =>
    route.request().method() === "POST" ? route.abort("connectionrefused") : route.fallback(),
  );
  await page.goto("/");
  await page.getByLabel("Funda-link").fill("https://www.funda.nl/detail/koop/utrecht/huis-1/43000000/");
  await page.getByRole("button", { name: "Ophalen" }).click();

  await expect(page.getByRole("alert")).toContainText("de server reageert niet");
  await expect(page.getByRole("button", { name: "Ophalen" })).toBeEnabled();
});
