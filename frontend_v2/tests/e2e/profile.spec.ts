import { rm } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

const profileDataFile = resolve(".data/playwright-profile-records.json");

test.beforeEach(async ({ page }) => {
  await useSignedInDemo(page);
  await rm(profileDataFile, { force: true });
});

test.afterEach(async () => {
  await rm(profileDataFile, { force: true });
});

async function createProfile(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/profile");
  await page.getByLabel("Name").fill("Alex Kim");
  await page.getByLabel("Research interests").fill("AI, Computer Vision");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
}

test("saved profile opens as a useful My Page and remains editable", async ({ browser, page }) => {
  await page.goto("/profile");
  await page.getByLabel("Name").fill("Alex Kim");
  await page.getByLabel("Research interests").fill("AI, Computer Vision");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByLabel("CV file").setInputFiles("tests/fixtures/sample-cv.pdf");
  await page.getByRole("button", { name: "Save profile" }).click();

  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit profile" })).toBeVisible();
  await expect(page.getByLabel("Name")).toHaveCount(0);
  await expect(page.getByText("sample-cv.pdf")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Saved professors" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Professors close to your interests" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
  await expect(page.getByLabel("Name")).toHaveCount(0);

  await page.getByRole("button", { name: "Edit profile" }).click();
  await expect(page.getByLabel("Name")).toHaveValue("Alex Kim");
  await expect(page.getByLabel("Research interests")).toHaveValue("AI, Computer Vision");
  await page.getByLabel("Name").fill("Jamie Kim");
  await page.getByLabel("Research interests").fill("HCI, Accessibility");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Jamie Kim’s Profile" })).toBeVisible();
  await expect(page.getByLabel("Saved research keywords").getByText("HCI", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Jamie Kim’s Profile" })).toBeVisible();

  const otherOwner = await browser.newContext();
  await useSignedInDemo(otherOwner);
  const otherPage = await otherOwner.newPage();
  await otherPage.goto("/profile");
  await expect(otherPage.getByRole("heading", { name: "Create research profile" })).toBeVisible();
  await otherOwner.close();

  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByRole("button", { name: "Delete all my data" }).click();
  await expect(page.getByRole("heading", { name: "Create research profile" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Create research profile" })).toBeVisible();
});

test("saved professor persists from discovery to My Page and can be removed", async ({ page }) => {
  await createProfile(page);
  await page.goto("/professors");
  const labCard = page.getByRole("heading", { name: "AI Systems Lab (Demo)" }).locator("..").locator("..");
  await labCard.getByRole("button", { name: "Save professor" }).click();
  await expect(labCard.getByRole("button", { name: "Saved" })).toBeVisible();

  await page.reload();
  const reloadedCard = page.getByRole("heading", { name: "AI Systems Lab (Demo)" }).locator("..").locator("..");
  await expect(reloadedCard.getByRole("button", { name: "Saved" })).toBeVisible();

  await page.goto("/profile");
  const savedRegion = page.getByRole("region", { name: "Saved professors" });
  await expect(savedRegion).toBeVisible();
  await expect(savedRegion.getByText("AI Systems Lab (Demo)")).toBeVisible();
  await expect(savedRegion.getByRole("link", { name: "View details" })).toHaveAttribute("href", "/professors/snu-demo-01");

  await savedRegion.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByText("No saved professors")).toBeVisible();
  await page.reload();
  await expect(page.getByText("No saved professors")).toBeVisible();
});
