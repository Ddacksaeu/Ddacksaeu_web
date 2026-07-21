import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("calendar event form uses labelled designed controls", async ({ page }) => {
  // Given
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.route("**/api/backend/me/calendar-events", async (route) => {
    await route.fulfill({ json: { items: [] } });
  });
  await page.route("**/api/backend/admissions", async (route) => {
    await route.fulfill({ json: { items: [] } });
  });

  // When
  await page.goto("/calendar");

  // Then
  const quickAdd = page.getByRole("form", { name: "Quick add reminder" });
  const title = quickAdd.getByLabel("Reminder");
  const date = quickAdd.getByLabel("Date", { exact: true });
  const kind = quickAdd.getByLabel("Type");
  const addButton = quickAdd.getByRole("button", { name: "Add reminder" });
  const exportButton = page.getByRole("button", { name: "Export calendar" });

  await expect(title).toBeVisible();
  await expect(date).toBeVisible();
  await expect(kind).toBeVisible();
  await expect(title).toHaveCSS("height", "44px");
  await expect(title).toHaveCSS("border-radius", "10px");
  await expect(date).toHaveCSS("height", "44px");
  await expect(kind).toHaveCSS("height", "44px");
  await expect(addButton).toHaveCSS("min-height", "44px");
  await expect(addButton).toHaveCSS("border-radius", "10px");
  await expect(exportButton).toHaveCSS("height", "46px");
  await expect(exportButton).toHaveCSS("border-radius", "10px");

  await page.setViewportSize({ width: 375, height: 812 });
  const mobileGeometry = await page.evaluate(() => {
    const personal = document.querySelector<HTMLElement>(".calendar-month-panel");
    const official = document.querySelector<HTMLElement>(".calendar-upcoming");
    const timeline = document.querySelector<HTMLElement>(".calendar-month-heading > div > span");
    const heading = document.querySelector<HTMLElement>(".calendar-month-heading h2");
    const count = document.querySelector<HTMLElement>(".calendar-month-heading > span");
    if (!personal || !official || !timeline || !heading || !count) throw new Error("Calendar mobile elements are missing.");
    return {
      personalY: personal.getBoundingClientRect().y,
      officialY: official.getBoundingClientRect().y,
      timelineHeight: timeline.getBoundingClientRect().height,
      headingHeight: heading.getBoundingClientRect().height,
      countHeight: count.getBoundingClientRect().height,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    };
  });
  expect(mobileGeometry.personalY).toBeLessThan(mobileGeometry.officialY);
  expect(mobileGeometry.timelineHeight).toBeLessThan(24);
  expect(mobileGeometry.headingHeight).toBeLessThan(40);
  expect(mobileGeometry.countHeight).toBeLessThan(24);
  expect(mobileGeometry.overflow).toBeFalsy();
});
