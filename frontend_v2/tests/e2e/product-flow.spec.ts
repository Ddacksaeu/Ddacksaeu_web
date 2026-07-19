import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Given a new applicant, when onboarding is completed, then the personalized dashboard is shown", async ({ page }) => {
  // Given
  await page.goto("/login");
  await page.getByLabel("Username").fill("researcher");
  await page.getByLabel("Password").fill("demo");

  // When
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/onboarding/);
  expect(new URL(page.url()).search).toBe("");
  await page.getByLabel("Preferred university").selectOption("Seoul National University");
  await page.getByLabel("Target major and research interests").fill("Computer Vision");
  await page.getByRole("radio", { name: "Master’s" }).check();
  await page.getByRole("button", { name: "Complete setup" }).click();

  // Then
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/);
  expect(new URL(page.url()).search).toBe("");
  await expect(page.getByRole("heading", { name: "Home", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Professors close to your interests" })).toBeVisible();
  await expect(page.getByText("Profile ready · Next: add a CV")).toBeVisible();
  const savedProfile = await page.evaluate(async () => {
    const response = await fetch("/api/profile");
    return response.json() as Promise<{ readonly profile: { readonly preferredUniversity: string; readonly applicationTerm: string; readonly degreeProgram: string } }>;
  });
  expect(savedProfile.profile).toMatchObject({ preferredUniversity: "Seoul National University", applicationTerm: "Spring 2027", degreeProgram: "Master's" });
  await expect(page.getByRole("heading", { name: "Labs with recruitment to verify" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Upcoming dates" })).toBeVisible();
});

test("Given the dashboard, when a professor is explored, then detail and contact drafting are reachable", async ({ page }) => {
  // Given
  await useSignedInDemo(page);
  await page.goto("/professors");

  // When
  await page.getByLabel("Search professors, labs, or keywords").fill("Vision");

  // Then
  await expect(page.getByText(/2 professors found/)).toBeVisible();
  await page.getByRole("link", { name: "View details" }).first().click();
  await expect(page).toHaveURL(/professors\/snu-demo-02$/, { timeout: 30000 });
  await expect(page.getByRole("heading", { name: /Intelligent Vision Lab/ })).toBeVisible();
  await expect(page.getByText("Create a profile to compare", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent research and paper preview" })).toBeVisible();
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

test("professor detail keeps project and paper titles intact on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await useSignedInDemo(page);
  await page.goto("/professors/snu-demo-02");

  const project = page.getByText("Reproducible benchmark for student researchers", { exact: true });
  const paper = page.getByText(/Adaptive framework for representation learning$/, { exact: true });
  await expect(project).toHaveCSS("word-break", "keep-all");
  await expect(paper).toHaveCSS("word-break", "keep-all");
});

test("Given the signed-in workspace, when core tools are opened, then every IA destination has a usable screen", async ({ page }) => {
  // Given / When / Then
  await useSignedInDemo(page);
  for (const target of [
    { path: "/calendar", heading: "See admissions deadlines" },
    { path: "/profile", heading: "research profile" },
  ]) {
    await page.goto(target.path);
    await expect(page.getByRole("heading", { name: new RegExp(target.heading), level: 1 })).toBeVisible();
  }
});

test("Given no profile, when a demo profile is saved, then My Page reveals the saved profile and recommendations", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Create research profile", level: 1 })).toBeVisible();
  await page.getByLabel("Name").fill("Test Researcher");
  await page.getByLabel("Research interests").fill("computer vision, HCI");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByRole("button", { name: "Save profile" }).click();

  await expect(page.getByRole("heading", { name: "Test Researcher’s Profile", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Professors close to your interests" })).toBeVisible();
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
