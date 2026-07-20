import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

test("Given a calendar reminder is added, when the page reloads, then it remains", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/calendar");

  await page.getByLabel("Reminder", { exact: true }).fill("Persistent application reminder");
  await page.getByLabel("Date", { exact: true }).fill("2026-12-02");
  await page.getByRole("button", { name: "Add reminder" }).click();
  const reminder = page.getByRole("heading", { name: "Persistent application reminder" });
  await expect(reminder).toBeVisible();

  await page.reload();
  await expect(reminder).toBeVisible();
});

test("Given a contact draft is saved, when My Page opens, then the draft can be resumed", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/contact?professor=LAB_E10BFB94AFD8");
  await expect(page.getByLabel("Professor", { exact: true })).toHaveValue("황형주");
  await page.getByLabel("Subject").fill("Research inquiry");
  await page.getByLabel("Email body").fill("Draft body");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.goto("/profile");

  const draftSection = page.getByRole("region", { name: "Outreach draft in progress" });
  await expect(draftSection.getByText("황형주 Outreach email")).toBeVisible();
  await page.reload();
  await expect(draftSection.getByText("황형주 Outreach email")).toBeVisible();
  await draftSection.getByRole("link", { name: "Continue editing" }).click();
  await expect(page).toHaveURL(/\/contact\?professor=LAB_E10BFB94AFD8/);
  await expect(page.getByLabel("Professor", { exact: true })).toHaveValue("황형주");
  await expect(page.getByLabel("Subject")).toHaveValue("Research inquiry");
  await expect(page.getByLabel("Email body")).toHaveValue("Draft body");
  await expect(page.getByText("Restored your saved draft. Review it before copying or saving again.")).toBeVisible();

  await page.goto("/profile");
  await draftSection.getByRole("button", { name: "Delete" }).click();
  await expect(draftSection).toBeHidden();
  await page.reload();
  await expect(draftSection).toBeHidden();
});
