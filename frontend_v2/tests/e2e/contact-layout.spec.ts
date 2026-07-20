import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Generate draft is separated from and aligned with its textarea", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.goto("/contact?professor=LAB_E10BFB94AFD8");

  const details = page.getByLabel("Details to include");
  const regenerate = page.getByRole("button", { name: "Generate draft" });
  const [detailsBox, regenerateBox] = await Promise.all([
    details.boundingBox(),
    regenerate.boundingBox(),
  ]);

  expect(detailsBox).not.toBeNull();
  expect(regenerateBox).not.toBeNull();
  expect(regenerateBox!.x).toBe(detailsBox!.x);
  expect(regenerateBox!.y - (detailsBox!.y + detailsBox!.height)).toBe(12);
});
