import { expect, test } from "@playwright/test";

test("Given the public landing, when a visitor opens it, then entry paths are clear", async ({ page }) => {
  // Given / When
  await page.goto("/");

  // Then
  await expect(page.getByRole("heading", { name: /Find professors who match your/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Find professors" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create my profile" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Explore labs at leading universities" })).toBeVisible();
  await expect(page.locator(".university-marquee-group").first().getByRole("listitem")).toHaveCount(4);
});

test("Given the university marquee, when it receives focus, then the motion pauses", async ({ page }) => {
  await page.goto("/");

  const marquee = page.locator(".university-marquee");
  const track = page.locator(".university-marquee-track");
  await expect(track).toHaveCSS("animation-name", "university-marquee");
  await marquee.focus();
  await expect(track).toHaveCSS("animation-play-state", "paused");
});

test("Given reduced motion, when the landing opens, then university logos remain static", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");

  await expect(page.locator(".university-marquee-track")).toHaveCSS("animation-name", "none");
  await expect(page.locator('.university-marquee-group[aria-hidden="true"]')).toBeHidden();
});

test("Given a mobile landing, university logos remain visible without an empty marquee frame", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");

  await expect(page.locator(".university-marquee-track")).toHaveCSS("animation-name", "none");
  const firstLogo = page.locator(".university-marquee-group").first().getByRole("listitem").first();
  const visibleInsideRail = await firstLogo.evaluate((element) => {
    const rail = element.closest(".university-marquee");
    if (rail === null) return false;
    const logoBounds = element.getBoundingClientRect();
    const railBounds = rail.getBoundingClientRect();
    return logoBounds.left < railBounds.right && logoBounds.right > railBounds.left;
  });
  expect(visibleInsideRail).toBe(true);
});

test("Given an unknown route, when a visitor opens it, then the branded recovery page is shown", async ({ page }) => {
  await page.goto("/does-not-exist");

  await expect(page.getByRole("heading", { name: "Lost your way?" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Return to demo home" })).toBeVisible();
});
