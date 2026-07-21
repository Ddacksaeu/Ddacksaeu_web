import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";
import { getFirstBackendLab } from "./backend-lab";

test("Given a calendar reminder is added, when the page reloads, then it remains", async ({ page }) => {
  await useSignedInDemo(page);
  await page.goto("/calendar");

  const quickAdd = page.getByRole("form", { name: "Quick add reminder" });
  await quickAdd.getByLabel("Reminder", { exact: true }).fill("Persistent application reminder");
  await quickAdd.getByLabel("Date", { exact: true }).fill("2026-12-02");
  await quickAdd.getByRole("button", { name: "Add reminder" }).click();
  const reminder = page.getByRole("heading", { name: "Persistent application reminder" });
  await expect(reminder).toBeVisible();

  await page.reload();
  await expect(reminder).toBeVisible();
});

test("Given a contact draft is saved, when My Page opens, then the draft can be resumed", async ({ page, request }) => {
  await useSignedInDemo(page);
  const lab = await getFirstBackendLab(request);
  await page.goto(`/contact?professor=${lab.id}`);
  await expect(page.getByLabel("Professor", { exact: true })).toHaveValue(lab.professorName);
  await page.getByLabel("Subject").fill("Research inquiry");
  await page.getByLabel("Email body").fill("Draft body");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.goto("/profile");

  const draftSection = page.getByRole("region", { name: "Outreach draft in progress" });
  await expect(draftSection.getByText(`${lab.professorName} Outreach email`)).toBeVisible();
  await page.reload();
  await expect(draftSection.getByText(`${lab.professorName} Outreach email`)).toBeVisible();
  await draftSection.getByRole("link", { name: "Continue editing" }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("professor")).toBe(lab.id);
  await expect(page.getByLabel("Professor", { exact: true })).toHaveValue(lab.professorName);
  await expect(page.getByLabel("Subject")).toHaveValue("Research inquiry");
  await expect(page.getByLabel("Email body")).toHaveValue("Draft body");
  await expect(page.getByText("Restored your saved draft. Edit it, then run the local review.")).toBeVisible();

  await page.goto("/profile");
  await draftSection.getByRole("button", { name: "Delete" }).click();
  await expect(draftSection).toBeHidden();
  await page.reload();
  await expect(draftSection).toBeHidden();
});
