import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("catalog results align beside the search rail on desktop", async ({ page }) => {
  // Given
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.route("**/api/backend/me/favorites", async (route) => {
    await route.fulfill({ json: { labIds: [] } });
  });

  // When
  await page.goto("/professors");
  const card = page.getByRole("article").first();
  await expect(card).toBeVisible();

  // Then
  const searchBox = await page.locator(".catalog-search-field").boundingBox();
  const resultsBox = await page.locator(".catalog-results-area").boundingBox();
  const cardBox = await card.boundingBox();
  if (searchBox === null || resultsBox === null || cardBox === null) {
    throw new Error("Catalog layout boxes must be measurable.");
  }
  expect(resultsBox.x).toBeGreaterThan(searchBox.x + searchBox.width);
  expect(cardBox.x).toBe(resultsBox.x);
  expect(cardBox.width).toBeLessThanOrEqual(resultsBox.width);

  const matchButton = page.getByRole("button", { name: "Match with my CV" });
  const matchBox = await matchButton.boundingBox();
  if (matchBox === null) {
    throw new Error("CV match button must be measurable.");
  }
  expect(await matchButton.evaluate((button) => button.scrollWidth <= button.clientWidth)).toBeTruthy();
  expect(matchBox.height).toBe(44);
});
