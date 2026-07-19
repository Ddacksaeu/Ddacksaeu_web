import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Start analysis stays separated from and aligned with the application goal", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/cv");

  const select = page.getByLabel("Application goal");
  const button = page.getByRole("button", { name: "Start analysis" });
  const geometry = await Promise.all([select.boundingBox(), button.boundingBox()]);
  const [selectBox, buttonBox] = geometry;

  expect(selectBox).not.toBeNull();
  expect(buttonBox).not.toBeNull();
  expect(buttonBox!.y - (selectBox!.y + selectBox!.height)).toBe(22);
  expect(buttonBox!.x).toBe(selectBox!.x);
  expect(buttonBox!.width).toBe(selectBox!.width);
});
