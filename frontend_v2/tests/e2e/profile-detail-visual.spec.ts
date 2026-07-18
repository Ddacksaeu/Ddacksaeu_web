import { mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

const dataFile = resolve(".data/playwright-profile-records.json");
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
  await rm(dataFile, { force: true });
});

test.afterEach(async () => {
  await rm(dataFile, { force: true });
});

test("captures every affected profile and professor state", async ({ page }) => {
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Create research profile" })).toBeVisible();
  await captureBreakpoints(page, "profile-empty");

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByLabel("Name").fill("Alex Kim");
  await page.getByLabel("Research interests").fill("AI, Computer Vision");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();

  await page.goto("/professors");
  const saveButton = page.getByRole("button", { name: "Save professor" }).first();
  await expect(saveButton).toBeEnabled();
  await saveButton.click();
  await expect(page.getByRole("button", { name: "Saved" }).first()).toBeVisible();
  await captureBreakpoints(page, "professors-saved");

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
  await captureBreakpoints(page, "profile-saved");

  await page.evaluate(() => {
    window.localStorage.setItem("ddaksaewoo:contact-draft", JSON.stringify({
      professor: "Ara Kim",
      draft: "Hello Ara Kim, I am continuing this outreach email based on my saved research experience.",
    }));
  });
  await page.reload();
  await expect(page.getByRole("region", { name: "Outreach draft in progress" })).toBeVisible();
  await captureBreakpoints(page, "profile-contact-draft");

  await page.goto("/professors/snu-demo-01");
  await expect(page.getByRole("heading", { name: "AI Systems Lab (Demo)" })).toBeVisible();
  await expect(page.getByText("1 exact keyword match", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent research and paper preview" })).toBeVisible();
  await captureBreakpoints(page, "professor-detail");
});
