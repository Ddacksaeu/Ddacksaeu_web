import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Regenerate draft is separated from and aligned with its textarea", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.goto("/professors/kaist-demo-05");

  const details = page.getByLabel("Details to include");
  const regenerate = page.getByRole("button", { name: "Regenerate draft" });
  const [detailsBox, regenerateBox] = await Promise.all([
    details.boundingBox(),
    regenerate.boundingBox(),
  ]);

  expect(detailsBox).not.toBeNull();
  expect(regenerateBox).not.toBeNull();
  expect(regenerateBox!.x).toBe(detailsBox!.x);
  expect(regenerateBox!.y - (detailsBox!.y + detailsBox!.height)).toBe(12);
});
