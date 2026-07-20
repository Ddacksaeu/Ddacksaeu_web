import { expect, test } from "@playwright/test";

test.describe("real backend home", () => {
  test.skip(process.env["PLAYWRIGHT_RELEASE_SMOKE"] !== "1", "requires imported lab data");

  test("Given imported labs, when the home radar opens its first lab, then the real detail page loads", async ({ page }) => {
    await page.goto("/");
    const firstLab = page.locator(".home-radar ol a").first();

    await expect(firstLab).toHaveAttribute("href", /^\/professors\/LAB_/);
    await firstLab.click();
    await expect(page).toHaveURL(/\/professors\/LAB_/);
    await expect(page.locator("h1")).toBeVisible();
  });
});
