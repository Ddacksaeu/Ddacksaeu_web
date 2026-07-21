import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";
import { getFirstBackendLab } from "./backend-lab";

test("Generate draft is separated from and aligned with its textarea", async ({ page, request }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  const lab = await getFirstBackendLab(request);
  await page.goto(`/contact?professor=${lab.id}`);

  const details = page.getByLabel("Verified lab topics");
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
