import { mkdir } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

const evidenceDir = ".omo/evidence/profile-detail-qa";
const viewports = [
  { name: "desktop", width: 1280, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 375, height: 812 },
] as const;

async function captureBreakpoints(page: Page, slug: string): Promise<void> {
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.evaluate(() => window.scrollTo(0, 0));
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow).toBe(false);
    await page.screenshot({ path: evidenceDir + "/" + slug + "-" + viewport.name + ".png", fullPage: true });
  }
}

test.beforeAll(async () => {
  await mkdir(evidenceDir, { recursive: true });
});

test.beforeEach(async ({ page }) => {
  await useSignedInDemo(page);
});

test("captures every affected profile and professor state", async ({ page }) => {
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Playwright Researcher’s Profile" })).toBeVisible();
  await captureBreakpoints(page, "profile-default");

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Edit profile" }).click();
  await captureBreakpoints(page, "profile-edit");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByLabel("Name").fill("Alex Kim");
  await page.getByLabel("Research interests").fill("AI, Computer Vision");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();

  await page.goto("/professors");
  const saveButton = page.getByRole("button", { name: "Save lab" }).first();
  await expect(saveButton).toBeEnabled();
  await saveButton.click();
  await expect(page.getByRole("button", { name: "Remove saved lab" }).first()).toBeVisible();
  await captureBreakpoints(page, "professors-saved");

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
  await captureBreakpoints(page, "profile-saved");

  await page.evaluate(() => {
    window.localStorage.setItem("ddaksaewoo:contact-draft", JSON.stringify({
      labId: "LAB_E10BFB94AFD8",
      professor: "황형주",
      subject: "Research inquiry",
      body: "I am continuing this outreach email based on my saved research experience.",
    }));
  });
  await page.reload();
  await expect(page.getByRole("region", { name: "Outreach draft in progress" })).toBeVisible();
  await captureBreakpoints(page, "profile-contact-draft");

  await page.goto("/professors/LAB_E10BFB94AFD8");
  await expect(page.getByRole("article", { name: "Professor research profile" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Application context" })).toBeVisible();
  await captureBreakpoints(page, "professor-detail");
});
