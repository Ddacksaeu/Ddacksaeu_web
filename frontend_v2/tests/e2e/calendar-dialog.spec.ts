import { mkdir } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

const EVIDENCE_DIR = "output/playwright/calendar-dialog-qa";

test.beforeAll(async () => {
  await mkdir(EVIDENCE_DIR, { recursive: true });
});

type Reminder = {
  id: string;
  title: string;
  kind: "apply" | "contact" | "docs" | "interview";
  date: string;
  labId: null;
  memo: null;
  createdAt: string;
  updatedAt: string;
};

test("calendar date dialog resets, edits, deletes, and restores focus", async ({ page }) => {
  const selectedDate = "2026-07-22";
  const timestamp = "2026-07-21T00:00:00Z";
  let reminder: Reminder | null = null;

  await page.setViewportSize({ width: 1280, height: 900 });
  await useSignedInDemo(page);
  await page.route("**/api/backend/admissions", (route) => route.fulfill({ json: { items: [] } }));
  await page.route("**/api/backend/me/calendar-events**", async (route) => {
    const request = route.request();
    const method = request.method();
    if (method === "GET") {
      await route.fulfill({ json: { items: reminder ? [reminder] : [] } });
      return;
    }
    if (method === "DELETE") {
      reminder = null;
      await route.fulfill({ status: 204, body: "" });
      return;
    }

    const payload = request.postDataJSON() as Pick<Reminder, "title" | "kind" | "date">;
    reminder = {
      id: "dialog-reminder",
      title: payload.title,
      kind: payload.kind,
      date: payload.date,
      labId: null,
      memo: null,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    await route.fulfill({ json: reminder });
  });

  await page.goto(`/calendar?date=${selectedDate}`);
  await expect(page.getByRole("button", { name: "Add reminder" }).first()).toBeEnabled();

  const dateButton = page.getByRole("button", { name: new RegExp(`^${selectedDate}`) });
  await dateButton.click();
  const dialog = page.getByRole("dialog", { name: "Events on this date" });
  const editor = dialog.getByRole("form", { name: "Date reminder editor" });
  const reminderInput = editor.getByLabel("Reminder");
  await expect(dialog).toBeVisible();

  await page.screenshot({ path: `${EVIDENCE_DIR}/empty-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: `${EVIDENCE_DIR}/empty-mobile.png`, fullPage: true });
  await page.setViewportSize({ width: 1280, height: 900 });

  for (const control of [
    dialog.getByRole("button", { name: "Close date details" }),
    reminderInput,
    editor.getByLabel("Date"),
    editor.getByLabel("Type"),
    editor.getByRole("button", { name: "Add reminder" }),
  ]) {
    const box = await control.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);
  }

  await reminderInput.fill("Discard this draft");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(dateButton).toBeFocused();

  await dateButton.click();
  await expect(editor.getByLabel("Reminder")).toHaveValue("");
  const bounds = await dialog.boundingBox();
  expect(bounds).not.toBeNull();
  await page.mouse.click(Math.max(1, bounds!.x - 5), Math.max(1, bounds!.y - 5));
  await expect(dialog).toBeHidden();

  await dateButton.click();
  await editor.getByLabel("Reminder").fill("Dialog reminder");
  await editor.getByLabel("Type").selectOption("docs");
  await editor.getByRole("button", { name: "Add reminder" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("heading", { name: "Dialog reminder" })).toBeVisible();

  await dateButton.click();
  await dialog.getByRole("button", { name: "Edit" }).click();
  await expect(editor.getByLabel("Reminder")).toHaveValue("Dialog reminder");
  await page.screenshot({ path: `${EVIDENCE_DIR}/edit-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({ path: `${EVIDENCE_DIR}/edit-mobile.png`, fullPage: true });
  await page.setViewportSize({ width: 1280, height: 900 });

  await editor.getByLabel("Reminder").fill("Updated dialog reminder");
  await editor.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Updated dialog reminder" })).toBeVisible();

  await dateButton.click();
  page.once("dialog", (confirmation) => confirmation.accept());
  await dialog.getByRole("button", { name: "Delete" }).click();
  await expect(dialog.getByText("Updated dialog reminder")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Close date details" }).click();
  await expect(dialog).toBeHidden();
});

test("signed-in mobile navigation keeps every target at least 44 pixels", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await useSignedInDemo(page);
  await page.route("**/api/backend/me/calendar-events", (route) => route.fulfill({ json: { items: [] } }));
  await page.route("**/api/backend/admissions", (route) => route.fulfill({ json: { items: [] } }));
  await page.goto("/calendar");

  const targets = page.getByRole("navigation", { name: "Main navigation" }).locator("a, button");
  await expect(targets).toHaveCount(5);
  for (const target of await targets.all()) {
    const box = await target.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});
