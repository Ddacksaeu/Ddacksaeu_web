import { mkdir } from "node:fs/promises";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { z } from "zod";

import { useSignedInDemo } from "./demo-session";

const labSearchSchema = z.object({
  items: z.array(z.object({ id: z.string() })),
});
const evidenceDir = ".omo/evidence/professor-detail-adaptive";
const appOrigin = process.env["PLAYWRIGHT_APP_ORIGIN"] ?? "";
const viewports = [
  { name: "desktop", width: 1280, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 375, height: 812 },
] as const;

test.beforeAll(async () => {
  await mkdir(evidenceDir, { recursive: true });
});

async function getFirstBackendLabId(request: APIRequestContext): Promise<string> {
  const response = await request.get("http://127.0.0.1:8000/api/v1/labs?page=1&page_size=1");
  expect(response.ok()).toBe(true);
  const result = labSearchSchema.parse(await response.json());
  const lab = result.items.at(0);
  if (lab === undefined) throw new RangeError("Professor detail layout requires at least one backend lab.");
  return lab.id;
}

async function useEmptyApplicationContext(page: Page): Promise<void> {
  await page.route("**/api/backend/me/profile", (route) => route.fulfill({
    status: 404,
    contentType: "application/json",
    body: JSON.stringify({ detail: "Profile not found" }),
  }));
  await page.route("**/api/backend/me/favorites", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ labIds: [] }),
  }));
}

async function captureBreakpoints(page: Page): Promise<void> {
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.evaluate(() => window.scrollTo(0, 0));
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow).toBe(false);
    await page.screenshot({
      path: `${evidenceDir}/professor-detail-${viewport.name}.png`,
      fullPage: true,
    });
  }
}

test("empty save status does not create a blank row between professor actions", async ({ page, request }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await useSignedInDemo(page);
  await useEmptyApplicationContext(page);
  const labId = await getFirstBackendLabId(request);
  await page.goto(`${appOrigin}/professors/${labId}`);

  const saveButton = page.getByRole("button", { name: /Save professor|Remove saved professor/ });
  const status = page.locator(".detail-save-control span");
  const outreachLink = page.getByRole("link", { name: "Create outreach email draft" });

  await expect(saveButton).toBeVisible();
  await expect(saveButton).toHaveAttribute("aria-pressed", "false");
  await expect(saveButton.locator("svg")).toBeVisible();
  expect((await saveButton.textContent())?.trim()).toBe("");
  await expect(status).toHaveCSS("display", "none");

  const [saveBox, outreachBox] = await Promise.all([
    saveButton.boundingBox(),
    outreachLink.boundingBox(),
  ]);

  expect(saveBox).not.toBeNull();
  expect(outreachBox).not.toBeNull();
  expect(saveBox!.width).toBe(44);
  expect(saveBox!.height).toBe(44);
  expect(outreachBox!.y - (saveBox!.y + saveBox!.height)).toBe(12);
});

test("professor detail adapts its sections to the available backend data", async ({ page, request }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await useEmptyApplicationContext(page);
  const labId = await getFirstBackendLabId(request);
  await page.goto(`${appOrigin}/professors/${labId}`);

  const researchProfile = page.getByRole("article", { name: "Professor research profile" });
  const applicationContext = page.getByRole("complementary", { name: "Application context" });
  const researchSections = researchProfile.locator(":scope > section");

  await expect(researchSections).toHaveCount(3);
  await expect(researchProfile.getByRole("heading", { name: "Lab overview" })).toBeVisible();
  await expect(researchProfile.getByRole("heading", { name: "Recent publication" })).toBeVisible();
  await expect(researchProfile.getByRole("heading", { name: "Research focus" })).toHaveCount(0);
  await expect(researchProfile.getByRole("heading", { name: "Lab facts" })).toHaveCount(0);
  await expect(researchProfile.getByTestId("paper-preview")).toHaveCount(1);
  await expect(page.getByRole("note", { name: "Research focus from source" })).toBeVisible();
  await expect(applicationContext.getByRole("heading", { name: "Recruitment status" })).toBeVisible();
  await expect(applicationContext.getByText("Not verified", { exact: true })).toBeVisible();
  await expect(applicationContext).toContainText("graduate admissions notice");
  await expect(applicationContext).toHaveCSS("border-radius", "16px");
  await expect(applicationContext).toHaveCSS("border-left-width", "1px");
  await expect(page.getByRole("link", { name: "Create outreach email draft" })).toHaveCSS(
    "background-color",
    "rgb(49, 130, 246)",
  );

  const [researchBox, contextBox] = await Promise.all([
    researchProfile.boundingBox(),
    applicationContext.boundingBox(),
  ]);
  expect(researchBox).not.toBeNull();
  expect(contextBox).not.toBeNull();
  expect(contextBox!.x).toBeGreaterThan(researchBox!.x + researchBox!.width);
  expect(researchBox!.width).toBeGreaterThan(contextBox!.width);

  await captureBreakpoints(page);
  await expect(applicationContext).toHaveCSS("border-left-width", "1px");

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);

  await page.setViewportSize({ width: 1280, height: 1400 });
  await applicationContext.screenshot({ path: `${evidenceDir}/application-context-rest.png` });
  const outreachLink = page.getByRole("link", { name: "Create outreach email draft" });
  await outreachLink.hover();
  await expect(outreachLink).toHaveCSS("background-color", "rgb(27, 100, 218)");
  await applicationContext.screenshot({ path: `${evidenceDir}/application-context-hover-settled.png` });

  const saveButton = page.getByRole("button", { name: "Save professor" });
  await saveButton.focus();
  await expect(saveButton).toHaveCSS("outline-style", "solid");
  await applicationContext.screenshot({ path: `${evidenceDir}/application-context-save-focus.png` });

  await page.evaluate(() => { document.documentElement.style.zoom = "200%"; });
  const zoomOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(zoomOverflow).toBe(false);
});
