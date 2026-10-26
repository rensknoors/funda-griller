import { expect, test } from "@playwright/test";

test("page confirms it can reach the API", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Funda Griller" })).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("API: reachable");
});
