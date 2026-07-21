import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";
import { getFirstBackendLab } from "./backend-lab";

test("Given a new applicant, when onboarding is completed, then the personalized dashboard is shown", async ({ page }) => {
  const email = `product-flow-${Date.now()}@example.test`;
  // Given
  await page.goto("/login");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Name").fill("Product Flow");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("product-flow-password");

  // When
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/onboarding/);
  expect(new URL(page.url()).search).toBe("");
  await page.getByLabel("Preferred university").selectOption("Seoul National University");
  await page.getByLabel("Target major and research interests").fill("Computer Vision");
  await page.getByRole("radio", { name: "Master’s" }).check();
  await page.locator('input[name="cv"]').setInputFiles({
    name: "product-flow-cv.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Computer vision graduate applicant with Python and PyTorch skills. Built multimodal medical imaging and object detection research projects. Interested in representation learning, human-centered AI, and robust machine learning."),
  });
  await page.getByRole("button", { name: "Complete setup" }).click();

  // Then
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/);
  expect(new URL(page.url()).search).toBe("");
  await expect(page.getByRole("heading", { name: "Home", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Professors close to your interests" })).toBeVisible();
  await expect(page.getByRole("progressbar", { name: "Application readiness: 80%" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Next: save a professor/i })).toBeVisible();
  const savedProfile = await page.evaluate(async () => {
    const response = await fetch("/api/profile");
    return response.json() as Promise<{ readonly profile: { readonly preferredUniversity: string; readonly applicationTerm: string; readonly degreeProgram: string } }>;
  });
  expect(savedProfile.profile).toMatchObject({ preferredUniversity: "Seoul National University", applicationTerm: "Spring 2027", degreeProgram: "Master's" });
  await expect(page.getByRole("heading", { name: "Application tasks to verify" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Upcoming dates" })).toBeVisible();
});

test("Given the dashboard, when a professor is explored, then detail and contact drafting are reachable", async ({ page }) => {
  // Given
  await useSignedInDemo(page);
  await page.goto("/professors");

  // When
  await page.getByLabel("Search professors, labs, or keywords").fill("Vision");

  // Then
  const results = page.getByRole("region", { name: "Professor search results" });
  await expect(results.getByRole("article").first()).toBeVisible();
  await results.getByRole("link", { name: "View details" }).first().click();
  await expect(page).toHaveURL(/professors\/[^/?#]+$/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Application context" })).toBeVisible();
  await page.getByRole("link", { name: "Create outreach email draft" }).click();
  await expect(page.getByRole("heading", { name: "Outreach email draft" })).toBeVisible();
});

test("professor filters use a labelled drawer on tablet", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await useSignedInDemo(page);
  await page.goto("/professors");

  const trigger = page.getByRole("button", { name: "Open professor search filters" });
  const filters = page.getByRole("region", { name: "Professor search filters" });
  await expect(trigger).toBeVisible();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await expect(filters).toBeHidden();

  await trigger.click();
  await expect(page.getByRole("button", { name: "Close professor search filters" })).toHaveAttribute("aria-expanded", "true");
  await expect(filters).toBeVisible();
  await expect(page.getByLabel("Search professors, labs, or keywords")).toBeVisible();
});

test("professor filter selections are optically centered inside their controls", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/professors");

  const selects = page.locator(".catalog-select-field select");
  await expect(selects).toHaveCount(2);
  for (const select of await selects.all()) {
    await expect(select).toHaveCSS("height", "48px");
    await expect(select).toHaveCSS("padding-top", "0px");
    await expect(select).toHaveCSS("padding-bottom", "1px");
  }
});

test("professor results keep compact spacing below the result count", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.goto("/professors");

  const toolbar = page.locator(".catalog-result-toolbar");
  const firstCard = page.locator(".catalog-card").first();
  await expect(toolbar).toBeVisible();
  await expect(firstCard).toBeVisible();

  const [toolbarBox, cardBox] = await Promise.all([toolbar.boundingBox(), firstCard.boundingBox()]);
  expect(toolbarBox).not.toBeNull();
  expect(cardBox).not.toBeNull();
  const gap = cardBox!.y - (toolbarBox!.y + toolbarBox!.height);
  expect(gap).toBeGreaterThanOrEqual(8);
  expect(gap).toBeLessThanOrEqual(16);
});

test("professor detail remains usable on mobile when publication data is unavailable", async ({ page, request }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await useSignedInDemo(page);
  const lab = await getFirstBackendLab(request);
  await page.goto(`/professors/${lab.id}`);

  await expect(page.getByRole("article", { name: "Professor research profile" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("Given the signed-in workspace, when core tools are opened, then every IA destination has a usable screen", async ({ page }) => {
  // Given / When / Then
  await useSignedInDemo(page);
  for (const target of [
    { path: "/calendar", heading: "See admissions deadlines" },
    { path: "/profile", heading: "Profile$" },
  ]) {
    await page.goto(target.path);
    await expect(page.getByRole("heading", { name: new RegExp(target.heading), level: 1 })).toBeVisible();
  }
});

test("Given an account profile, when it is updated, then My Page reveals the saved changes", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Playwright Researcher’s Profile", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "Edit profile" }).click();
  await expect(page.getByRole("heading", { name: "Edit research profile", level: 1 })).toBeVisible();
  await page.getByLabel("Name").fill("Test Researcher");
  await page.getByLabel("Research interests").fill("computer vision, HCI");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page.getByRole("heading", { name: "Test Researcher’s Profile", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Saved professors" })).toBeVisible();
});

test("Given the signed-in navigation, then My Page is always the final destination", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/dashboard");

  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation).toBeVisible();
  const labels = await navigation.getByRole("link").allTextContents();

  expect(labels.at(-1)?.trim()).toBe("Profile");
  expect(labels.indexOf("Calendar")).toBeLessThan(labels.indexOf("Profile"));
});
