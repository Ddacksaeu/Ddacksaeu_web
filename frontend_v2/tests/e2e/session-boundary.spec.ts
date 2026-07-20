import { expect, test } from "@playwright/test";

test("stale local sign-in redirects to login when the backend session is missing", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem("ddaksaewoo:demo-session", "signed-in");
    window.localStorage.setItem("ddaksaewoo:demo-onboarding", "complete");
  });
  await page.route("**/api/backend/me/profile", async (route) => {
    await route.fulfill({ json: { detail: "Not authenticated" }, status: 401 });
  });

  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Graduate school planning, all in one place" })).toBeVisible();
});
