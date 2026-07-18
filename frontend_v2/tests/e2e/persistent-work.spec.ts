import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Given a calendar task is checked, when the page reloads, then its progress remains", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/calendar");

  const task = page.getByRole("checkbox", { name: "Prepare professor-specific CV versions" });
  await task.check();
  await expect(page.getByText("2 / 4 complete")).toBeVisible();

  await page.reload();
  await expect(task).toBeChecked();
  await expect(page.getByText("2 / 4 complete")).toBeVisible();
});

test("Given a contact draft is saved, when My Page opens, then the draft can be resumed", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/profile");
  await page.getByLabel("Name").fill("Test Researcher");
  await page.getByLabel("Research interests").fill("computer vision, HCI");
  await page.getByLabel("I consent to saving this profile data").check();
  await page.getByRole("button", { name: "Save profile" }).click();

  await page.goto("/contact?professor=Ara%20Kim");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.goto("/profile");

  const draftSection = page.getByRole("region", { name: "Outreach draft in progress" });
  await expect(draftSection.getByText("Ara Kim Outreach email")).toBeVisible();
  await page.reload();
  await expect(draftSection.getByText("Ara Kim Outreach email")).toBeVisible();
  await draftSection.getByRole("link", { name: "Continue editing" }).click();
  await expect(page).toHaveURL(/\/contact\?professor=/);
  await expect(page.getByLabel("Professor", { exact: true })).toHaveValue("Ara Kim");

  await page.goto("/profile");
  await draftSection.getByRole("button", { name: "Delete" }).click();
  await expect(draftSection).toBeHidden();
  await page.reload();
  await expect(draftSection).toBeHidden();
});
