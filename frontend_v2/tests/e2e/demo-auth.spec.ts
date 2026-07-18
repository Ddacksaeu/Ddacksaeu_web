import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Given a completed demo session, when Sign in is chosen, then the login form is still shown", async ({ page }) => {
  // Given
  await useSignedInDemo(page);
  await page.goto("/");

  // When
  await page.getByRole("link", { name: "Sign in" }).click();
  await page.waitForLoadState("networkidle");

  // Then
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("Username")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});

test("Given the explicit login form and a completed demo session, when arbitrary credentials are submitted, then the dashboard opens", async ({ page }) => {
  // Given
  await useSignedInDemo(page);
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Username").fill("anything");
  await page.getByLabel("Password").fill("anything");

  // When
  await page.getByRole("button", { name: "Sign in" }).click();

  // Then
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Home", level: 1 })).toBeVisible();
});

test("Given a signed-out visitor, when a workspace URL is opened, then login is required", async ({ page }) => {
  // Given / When
  await page.goto("/dashboard");

  // Then
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Graduate school planning, all in one place" })).toBeVisible();
});

test("Given arbitrary demo credentials, when login and setup finish, then the workspace and logout are available", async ({ page }) => {
  // Given
  await page.goto("/login");
  await page.getByLabel("Username").fill("demo");
  await page.getByLabel("Password").fill("demo");

  // When
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await page.getByLabel("Preferred university").selectOption("Seoul National University");
  await page.getByLabel("Target major and research interests").fill("Computer Vision");
  await page.getByRole("radio", { name: "Master’s" }).check();
  await page.getByRole("button", { name: "Complete setup" }).click();

  // Then
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login$/);
});

test("Given sign-in without completed setup, workspace routes remain gated by onboarding", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("demo");
  await page.getByLabel("Password").fill("demo");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Tell us what you are looking for" })).toBeVisible();
});
