import { expect, test } from "@playwright/test";

import { useSignedInBeforeOnboarding, useSignedInDemo } from "./demo-session";

test("Given a completed account session, when Sign in is chosen, then the login form is still shown", async ({ page }) => {
  // Given
  await useSignedInDemo(page);
  await page.goto("/");

  // When
  await page.getByRole("link", { name: "Sign in" }).click();
  await page.waitForLoadState("networkidle");

  // Then
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});

test("Given invalid credentials, when sign in is submitted, then the login error remains visible", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("missing@example.test");
  await page.getByLabel("Password").fill("invalid-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator("p[aria-live='polite']")).toHaveText(/.+/);
});

test("Given a signed-out visitor, when a workspace URL is opened, then login is required", async ({ page }) => {
  // Given / When
  await page.goto("/dashboard");

  // Then
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Graduate school planning, all in one place" })).toBeVisible();
});

test("Given a new account, when signup and setup finish, then the workspace and logout are available", async ({ page }) => {
  const email = `auth-flow-${Date.now()}@example.test`;
  // Given
  await page.goto("/login");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Name").fill("Auth Flow");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("auth-flow-password");

  // When
  await page.getByRole("button", { name: "Create account" }).click();
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
  await useSignedInBeforeOnboarding(page);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Tell us what you are looking for" })).toBeVisible();
});

test("Given a scrolled onboarding page, the sticky header covers the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 400 });
  await useSignedInBeforeOnboarding(page);
  await page.goto("/onboarding");
  await expect(page).toHaveURL(/\/onboarding$/);

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  const header = page.locator(".site-header");
  const bounds = await header.boundingBox();
  const viewportWidth = await page.evaluate(
    () => document.documentElement.clientWidth,
  );

  expect(bounds?.x).toBe(0);
  expect(bounds?.width).toBe(viewportWidth);
});
