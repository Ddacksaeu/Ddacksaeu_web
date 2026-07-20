import { expect, test, type Page } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

async function mockEmptyDashboard(page: Page): Promise<void> {
  await page.route("**/api/backend/me/profile", async (route) => {
    await route.fulfill({
      json: {
        name: "New Researcher",
        affiliation: "POSTECH",
        status: "",
        program: "",
        interests: ["Machine learning"],
        skills: [],
        methodologies: [],
        projects: [],
        updatedAt: "2026-07-19T10:00:00Z",
      },
    });
  });
  await page.route("**/api/backend/recommendations", async (route) => {
    await route.fulfill({ status: 409, json: { error: { code: "http_409" } } });
  });
  await page.route("**/api/backend/me/calendar-events", async (route) => {
    await route.fulfill({ json: { items: [] } });
  });
  await page.route("**/api/backend/admissions", async (route) => {
    await route.fulfill({ json: { items: [] } });
  });
  await page.route("**/api/backend/documents/latest", async (route) => {
    await route.fulfill({ status: 404, json: { error: { code: "http_404" } } });
  });
  await page.route("**/api/backend/me/favorites", async (route) => {
    await route.fulfill({ json: { labIds: [] } });
  });
}

test("Given a new account without a CV, when the dashboard loads, then it shows an empty workspace", async ({ page }) => {
  // Given
  await useSignedInDemo(page);
  await mockEmptyDashboard(page);

  // When
  await page.goto("/dashboard");

  // Then
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
  await expect(page.getByText("No recommendations yet. Analyze a CV to create personalized matches.")).toBeVisible();
  const setupLink = page.getByRole("link", { name: "Application setup: 40% ready. Next: upload cv" });
  await expect(setupLink).toHaveAttribute("href", "/cv");
  await expect(page.getByRole("link", { name: "Upload CV", exact: true })).toHaveAttribute("href", "/cv");
  await expect(page.getByText("Could not load dashboard data.")).toHaveCount(0);
});
