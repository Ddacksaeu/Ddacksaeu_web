import { expect, test } from "@playwright/test";

test("Given the public landing, when a visitor opens it, then entry paths are clear", async ({ page }) => {
  // Given / When
  await page.goto("/");

  // Then
  await expect(page.getByRole("heading", { name: /Find professors who match your/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Find professors" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create my profile" })).toBeVisible();
  await expect(page.getByText("Try the demo flow", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Explore labs at leading universities" })).toBeVisible();
  const universityLogos = page.locator(".university-marquee-group").first().getByRole("img");
  await expect(universityLogos).toHaveCount(5);
  await expect(page.getByRole("img", { name: "Korea University logo" })).toBeVisible();
  const firstLogoItem = page.locator(".university-marquee-group").first().getByRole("listitem").first();
  await expect(firstLogoItem).toHaveCSS("border-top-width", "0px");
  await expect(firstLogoItem).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
});

test("Given the public header, when the landing renders, then the shrimp mark sits beside the brand", async ({ page }) => {
  // Given / When
  await page.goto("/");

  // Then
  const brand = page.getByRole("link", { name: "Ddaksaeu" });
  const mark = brand.locator(".brand-logo");
  await expect(mark).toBeVisible();
  await expect(mark).toHaveAttribute("src", /brand-shrimp.png/);
  await expect(mark).toHaveCSS("opacity", "0.95");
  const bounds = await mark.boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds!.width).toBe(24);
  expect(bounds!.height).toBe(24);
});

test("Given the profile CTA, when the landing page renders, then its single action is centered in the action column", async ({ page }) => {
  await page.goto("/");

  const actionColumn = page.locator(".home-bottom-actions");
  const createProfile = actionColumn.getByRole("link", { name: "Create my profile" });
  await expect(actionColumn).toBeVisible();
  await expect(createProfile).toBeVisible();
  const [columnBox, buttonBox] = await Promise.all([
    actionColumn.boundingBox(),
    createProfile.boundingBox(),
  ]);

  expect(columnBox).not.toBeNull();
  expect(buttonBox).not.toBeNull();
  expect(Math.abs(
    (columnBox!.x + columnBox!.width / 2) - (buttonBox!.x + buttonBox!.width / 2),
  )).toBeLessThanOrEqual(1);
});

test("Given the university marquee, when it receives focus, then the motion pauses", async ({ page }) => {
  await page.goto("/");

  const marquee = page.locator(".university-marquee");
  const track = page.locator(".university-marquee-track");
  await expect(track).toHaveCSS("animation-name", "university-marquee");
  await marquee.evaluate((element) => (element as HTMLElement).focus());
  await expect(marquee).toBeFocused();
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
  await expect(page.getByRole("link", { name: "Return home" })).toBeVisible();
});
