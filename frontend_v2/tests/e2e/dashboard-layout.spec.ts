import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("signed-in home uses a practical recommendation feed with an application overview", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { name: "Home", level: 1 })).toBeVisible();

  const recommendations = page.getByRole("region", { name: "Professor recommendations" });
  const overview = page.getByRole("complementary", { name: "Application overview" });
  await expect(recommendations).toBeVisible();
  await expect(overview).toBeVisible();
  await expect(recommendations.getByText("No recommendations yet. Analyze a CV to create personalized matches.")).toBeVisible();

  const recommendationBox = await recommendations.boundingBox();
  const overviewBox = await overview.boundingBox();
  expect(recommendationBox).not.toBeNull();
  expect(overviewBox).not.toBeNull();
  if (recommendationBox === null || overviewBox === null) {
    throw new Error("Dashboard columns must be visible");
  }
  expect(recommendationBox.x).toBeLessThan(overviewBox.x);
});

test("personalized signed-in home remains readable at every product breakpoint", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByLabel("Name").fill("Demo Researcher");
  await page.getByLabel("Research interests").fill("Computer Vision, Multimodal");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByRole("button", { name: "Save changes" }).click();

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Professors close to your interests" })).toBeVisible();

  for (const viewport of [
    { name: "desktop", width: 1280, height: 900 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "mobile", width: 375, height: 812 },
  ] as const) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);

    if (viewport.width <= 900) {
      const readinessBox = await page.getByRole("heading", { name: "Profile readiness" }).boundingBox();
      const recommendationsBox = await page
        .getByRole("heading", { name: "Professors close to your interests" })
        .boundingBox();
      const recruitmentBox = await page
        .getByRole("heading", { name: "Application tasks to verify" })
        .boundingBox();
      const datesBox = await page.getByRole("heading", { name: "Upcoming dates" }).boundingBox();
      expect(readinessBox).not.toBeNull();
      expect(recommendationsBox).not.toBeNull();
      expect(recruitmentBox).not.toBeNull();
      expect(datesBox).not.toBeNull();
      if (readinessBox === null || recommendationsBox === null || recruitmentBox === null || datesBox === null) {
        throw new Error("Responsive dashboard sections must be visible");
      }
      expect(readinessBox.y).toBeLessThan(recommendationsBox.y);
      expect(recommendationsBox.y).toBeLessThan(recruitmentBox.y);
      expect(recruitmentBox.y).toBeLessThan(datesBox.y);
    }

    await page.screenshot({
      path: `.omo/evidence/dashboard-redesign/profile-ready-${viewport.name}.png`,
      fullPage: true,
    });
  }
});
