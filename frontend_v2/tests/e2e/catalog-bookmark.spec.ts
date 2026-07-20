import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("professor card keeps its bookmark icon as the final action", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.route("**/api/backend/labs?*", async (route) => {
    await route.fulfill({
      json: {
        items: [{
          id: "lab-vision",
          name: "Vision Intelligence Lab",
          professorName: "Mina Park",
          university: "POSTECH",
          department: "Computer Science",
          field: "Computer Vision",
          summary: "Research in robust visual learning.",
          keywords: ["Computer Vision", "PyTorch"],
          homepageUrl: "https://example.edu/vision",
          updatedAt: "2026-07-19T09:00:00Z",
          recommendationScore: null,
          isFavorite: false,
        }],
        page: 1,
        pageSize: 100,
        total: 1,
      },
    });
  });
  await page.route("**/api/backend/me/favorites", async (route) => {
    await route.fulfill({ json: { labIds: [] } });
  });

  await page.goto("/professors");

  const card = page.getByRole("region", { name: "Professor search results" }).getByRole("article").first();
  await expect(card).toBeVisible();
  const actions = card.locator(".catalog-card-actions");
  const bookmark = actions.getByRole("button", { name: "Save lab" });
  await expect(bookmark).toBeVisible();
  await expect(bookmark.locator("svg")).toBeVisible();
  await expect(bookmark).toHaveAttribute("aria-pressed", "false");

  const lastAction = actions.locator(":scope > *").last();
  await expect(lastAction).toHaveAttribute("aria-label", "Save lab");
  await expect(bookmark).toHaveCSS("width", "44px");
  await expect(bookmark).toHaveCSS("height", "44px");
  await page.screenshot({
    path: ".omo/evidence/cv-professor-match/professors-bookmark-1280.png",
    fullPage: true,
  });
});
