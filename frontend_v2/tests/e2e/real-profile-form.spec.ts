import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

const profile = {
  name: "1234",
  affiliation: "POSTECH",
  status: "Preparing",
  program: "Master",
  interests: ["Computer Vision"],
  skills: [],
  methodologies: [],
  projects: [],
  updatedAt: "2026-07-19T09:00:00Z",
};

test("real profile fields use the product form layout instead of browser defaults", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.route("**/api/backend/me/profile", async (route) => {
    await route.fulfill({ json: profile });
  });
  await page.route("**/api/backend/documents/latest", async (route) => {
    await route.fulfill({ status: 404, json: { error: { code: "not_found" } } });
  });

  await page.goto("/profile");

  const form = page.locator("form.profile-card");
  const nameField = page.getByLabel("Name");
  const affiliationField = page.getByLabel("Affiliation");
  await expect(form).toBeVisible();
  await expect(nameField).toHaveCSS("height", "50px");
  await expect(nameField).toHaveCSS("border-radius", "12px");
  await expect(nameField.locator("xpath=..")).toHaveCSS("display", "grid");

  const [formBox, nameBox, affiliationBox] = await Promise.all([
    form.boundingBox(),
    nameField.boundingBox(),
    affiliationField.boundingBox(),
  ]);
  expect(formBox).not.toBeNull();
  expect(nameBox).not.toBeNull();
  expect(affiliationBox).not.toBeNull();
  if (formBox === null || nameBox === null || affiliationBox === null) {
    throw new Error("Profile form fields must have measurable layout");
  }

  expect(nameBox.width).toBeGreaterThan(formBox.width - 80);
  expect(affiliationBox.y).toBeGreaterThan(nameBox.y + nameBox.height);
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
});
