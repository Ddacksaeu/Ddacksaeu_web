import { expect, test } from "@playwright/test";

test.describe("release API smoke", () => {
  test.skip(process.env["PLAYWRIGHT_RELEASE_SMOKE"] !== "1", "requires the isolated release-smoke backend database");
  test("new applicant completes the supported API-backed workflow", async ({ page }) => {
    const email = `release-smoke-${Date.now()}@example.test`;
    await page.goto("/login");
    await page.getByRole("button", { name: "New here? Create an account" }).click();
    await page.getByLabel("Name").fill("Release Smoke"); await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("release-smoke-password");
    await page.getByRole("button", { name: "Create account" }).click(); await expect(page).toHaveURL(/\/onboarding$/);
    await page.evaluate(() => { localStorage.setItem("ddaksaewoo:demo-session", "signed-in"); localStorage.setItem("ddaksaewoo:demo-onboarding", "complete"); });
    await page.goto("/cv");
    await page.getByLabel("Select CV file").setInputFiles({ name: "release-smoke.txt", mimeType: "text/plain", buffer: Buffer.from("Computer vision and machine learning researcher with Python experience. Built a robotics perception project, evaluated neural models, documented reproducible experiments, and presented results to a faculty research group.") });
    await page.getByRole("button", { name: "Upload and analyze" }).click(); await expect(page.getByText("CV uploaded and analyzed successfully.")).toBeVisible();
    await page.goto("/professors"); await page.getByRole("button", { name: "Match with my CV" }).click();
    await expect(page.getByRole("button", { name: "Matching CV..." })).toBeDisabled();
    const recommendations = page.getByRole("region", { name: "CV-based professor recommendations" });
    await expect(recommendations.getByRole("heading", { name: "Best professor matches" })).toBeVisible({ timeout: 60_000 });
    const firstLab = recommendations.getByRole("link", { name: "View professor details" }).first(); await expect(firstLab).toBeVisible(); await firstLab.click();
    await expect(page).toHaveURL(/\/professors\/[^/?#]+$/, { timeout: 30_000 });
    await page.getByRole("button", { name: "Save professor" }).click(); await expect(page.getByText("Saved this professor.")).toBeVisible(); await page.reload();
    await expect(page.getByRole("button", { name: "Remove saved professor" })).toBeVisible();
    await page.getByRole("link", { name: "Create outreach email draft" }).click(); await expect(page.getByRole("heading", { name: "Outreach email draft" })).toBeVisible();
    await page.goto("/calendar"); await page.getByPlaceholder("Event title").fill("Release smoke reminder"); await page.locator('input[name="date"]').fill("2026-12-01"); await page.getByRole("button", { name: "Add reminder" }).click(); await expect(page.getByRole("heading", { name: "Release smoke reminder" })).toBeVisible();
    const ics = await page.request.get("/api/backend/admissions/export.ics"); expect(ics.ok()).toBeTruthy(); expect(ics.headers()["content-disposition"]).toContain("admissions-calendar.ics");
    await page.getByRole("button", { name: "Sign out" }).click(); await page.goto("/cv"); await expect(page).toHaveURL(/\/login$/);
  });
});
