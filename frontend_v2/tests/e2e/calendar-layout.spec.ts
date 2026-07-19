import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("University label sits above and aligns with the calendar filter", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.goto("/calendar");

  const label = page.locator('label[for="calendar-institution"]');
  const select = page.getByLabel("University");
  const [labelBox, selectBox] = await Promise.all([label.boundingBox(), select.boundingBox()]);

  expect(labelBox).not.toBeNull();
  expect(selectBox).not.toBeNull();
  expect(labelBox!.x).toBe(selectBox!.x);
  expect(selectBox!.y - (labelBox!.y + labelBox!.height)).toBe(8);
  await expect(label).toHaveCSS("font-size", "16px");

  const group = page.locator(".calendar-filter > div");
  const button = page.getByRole("button", { name: "View schedule" });
  await expect(group).toHaveCSS("gap", "12px");
  await expect(button).toHaveCSS("padding-left", "12px");
  await expect(button).toHaveCSS("padding-right", "12px");
});
