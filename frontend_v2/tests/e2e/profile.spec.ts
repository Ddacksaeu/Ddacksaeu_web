import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test.beforeEach(async ({ page }) => {
  await useSignedInDemo(page);
});

async function editProfile(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/profile");
  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByLabel("Name").fill("Alex Kim");
  await page.getByLabel("Research interests").fill("AI, Computer Vision");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
}

test("saved profile opens as a useful My Page and remains editable", async ({ browser, page }) => {
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Playwright Researcher’s Profile" })).toBeVisible();
  await page.getByRole("button", { name: "Edit profile" }).click();
  await page.getByLabel("Name").fill("Alex Kim");
  await page.getByLabel("Research interests").fill("AI, Computer Vision");
  await page.getByLabel("CV file").setInputFiles("tests/fixtures/sample-cv.pdf");
  await expect(page.getByText("PDF format verified. Text extraction will run when you save; image-only PDFs may not be readable.")).toBeVisible();
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page.getByRole("heading", { name: "Alex Kim’s Profile" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Edit profile" })).toBeVisible();
  await expect(page.getByLabel("Name")).toHaveCount(0);
  await expect(page.getByText("Profile saved, but the CV could not be analyzed. Try uploading it from CV Analysis.")).toBeVisible();
  await expect(page.getByText("sample-cv.pdf")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Saved professors" })).toBeVisible();

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
  await expect(otherPage.getByRole("heading", { name: "Playwright Researcher’s Profile" })).toBeVisible();
  await expect(otherPage.getByText("HCI", { exact: true })).toHaveCount(0);
  await otherOwner.close();
});

test("saved professor persists from discovery to My Page and can be removed", async ({ page }) => {
  await editProfile(page);
  await page.goto("/professors");
  const labCard = page.getByRole("region", { name: "Professor search results" }).getByRole("article").first();
  const labName = (await labCard.getByRole("heading", { level: 2 }).textContent())?.trim() ?? "";
  const detailHref = await labCard.getByRole("link", { name: "View details" }).getAttribute("href");
  const saveButton = labCard.getByRole("button", { name: "Save lab" });
  await expect(saveButton.locator("svg")).toBeVisible();
  expect((await saveButton.textContent())?.trim()).toBe("");
  await saveButton.click();
  await expect(labCard.getByRole("button", { name: "Remove saved lab" })).toHaveAttribute("aria-pressed", "true");

  await page.reload();
  const reloadedCard = page.getByRole("region", { name: "Professor search results" }).getByRole("article").first();
  await expect(reloadedCard.getByRole("button", { name: "Remove saved lab" })).toHaveAttribute("aria-pressed", "true");

  await page.goto("/profile");
  const savedRegion = page.getByRole("region", { name: "Saved professors" });
  await expect(savedRegion).toBeVisible();
  await expect(savedRegion.getByText(labName)).toBeVisible();
  await expect(savedRegion.getByRole("link", { name: "View details" })).toHaveAttribute("href", detailHref ?? "");

  await savedRegion.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByText("No saved professors")).toBeVisible();
  await page.reload();
  await expect(page.getByText("No saved professors")).toBeVisible();
});
