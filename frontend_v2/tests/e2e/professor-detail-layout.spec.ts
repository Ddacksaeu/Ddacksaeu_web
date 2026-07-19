import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("empty save status does not create a blank row between professor actions", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await useSignedInDemo(page);
  await page.goto("/professors/snu-demo-02");

  const saveButton = page.getByRole("button", { name: /Save professor|Remove saved professor/ });
  const status = page.locator(".detail-save-control span");
  const outreachLink = page.getByRole("link", { name: "Create outreach email draft" });

  await expect(saveButton).toBeVisible();
  await expect(saveButton).toHaveAttribute("aria-pressed", "false");
  await expect(saveButton.locator("svg")).toBeVisible();
  expect((await saveButton.textContent())?.trim()).toBe("");
  await expect(status).toHaveCSS("display", "none");

  const [saveBox, outreachBox] = await Promise.all([
    saveButton.boundingBox(),
    outreachLink.boundingBox(),
  ]);

  expect(saveBox).not.toBeNull();
  expect(outreachBox).not.toBeNull();
  expect(saveBox!.width).toBe(46);
  expect(saveBox!.height).toBe(46);
  expect(outreachBox!.y - (saveBox!.y + saveBox!.height)).toBe(12);
});

test("professor detail reads as an editorial profile with a supporting context rail", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.goto("/professors/snu-demo-02");

  const researchProfile = page.getByRole("article", { name: "Professor research profile" });
  const applicationContext = page.getByRole("complementary", { name: "Application context" });
  const researchSections = researchProfile.locator(":scope > section");
  const firstFocusItem = researchSections.nth(1).locator("article").first();

  await expect(researchSections).toHaveCount(5);
  await expect(researchSections.first()).toHaveCSS("border-radius", "0px");
  await expect(researchSections.first()).toHaveCSS("border-left-width", "0px");
  await expect(researchSections.nth(1)).toHaveCSS("border-top-width", "1px");
  await expect(firstFocusItem).toHaveCSS("border-radius", "0px");
  await expect(firstFocusItem).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(applicationContext).toHaveCSS("border-left-width", "1px");

  const [researchBox, contextBox] = await Promise.all([
    researchProfile.boundingBox(),
    applicationContext.boundingBox(),
  ]);
  expect(researchBox).not.toBeNull();
  expect(contextBox).not.toBeNull();
  expect(contextBox!.x).toBeGreaterThan(researchBox!.x + researchBox!.width);
  expect(researchBox!.width).toBeGreaterThan(contextBox!.width);

  await page.setViewportSize({ width: 375, height: 812 });
  await expect(applicationContext).toHaveCSS("border-left-width", "0px");
  await expect(applicationContext).toHaveCSS("border-top-width", "1px");

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});
