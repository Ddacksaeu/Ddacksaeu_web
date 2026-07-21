import { mkdir } from "node:fs/promises";

import { expect, test } from "@playwright/test";

import { useSignedInBeforeOnboarding, useSignedInDemo } from "./demo-session";
import { getFirstBackendLab } from "./backend-lab";

const PAGES = [
  { slug: "landing", path: "/", heading: "Find professors who match your" },
  { slug: "login", path: "/login", heading: "Graduate school planning," },
  { slug: "onboarding", path: "/onboarding", heading: "Tell us what you are looking for" },
  { slug: "dashboard", path: "/dashboard", heading: "Home" },
  { slug: "professors", path: "/professors", heading: "Find professors aligned with your research" },
  { slug: "professor-detail", path: "/professors", heading: "" },
  { slug: "cv", path: "/cv", heading: "CV and portfolio analysis" },
  { slug: "contact", path: "/contact", heading: "Outreach email draft" },
  { slug: "calendar", path: "/calendar", heading: "See admissions deadlines" },
  { slug: "profile", path: "/profile", heading: "Playwright Researcher’s Profile" },
  { slug: "not-found", path: "/does-not-exist", heading: "Lost your way?" },
] as const;

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 375, height: 812 },
] as const;

const EVIDENCE_DIR = "output/playwright/full-product-qa";

test.beforeAll(async () => {
  await mkdir(EVIDENCE_DIR, { recursive: true });
});

for (const target of PAGES) {
  test(target.slug + " renders at all product breakpoints", async ({ page, request }) => {
    const runtimeErrors: string[] = [];
    page.on("console", (message) => {
      const expectedEmptyStateRequest = /^Failed to load resource: the server responded with a status of (404|409) /.test(message.text());
      if (message.type() === "error" && !expectedEmptyStateRequest) runtimeErrors.push(message.text());
    });
    page.on("pageerror", (error) => runtimeErrors.push(error.message));
    page.on("response", (response) => {
      if (response.status() < 400) return;
      const pathname = new URL(response.url()).pathname;
      const expectedEmptyState = response.status() === 404 && pathname === "/api/backend/documents/latest"
        || response.status() === 409 && pathname === "/api/backend/recommendations"
        || response.status() === 404 && target.slug === "not-found" && pathname === "/does-not-exist";
      if (!expectedEmptyState) {
        runtimeErrors.push(`HTTP ${response.status()} ${pathname}`);
      }
    });
    if (target.path !== "/" && target.path !== "/login" && target.slug !== "not-found") {
      await (target.path === "/onboarding" ? useSignedInBeforeOnboarding(page) : useSignedInDemo(page));
    }
    const lab = target.slug === "professor-detail" || target.slug === "contact" ? await getFirstBackendLab(request) : null;
    const path = target.slug === "professor-detail" ? `/professors/${lab?.id}` : target.slug === "contact" ? `/contact?professor=${lab?.id}` : target.path;
    const heading = target.slug === "professor-detail" ? lab?.name ?? "" : target.heading;
    await page.goto(path);
    await expect(page.getByRole("heading", { name: new RegExp(heading), level: 1 })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/\bDemo\b|\(Demo\)|product testing|not real recruitment/i);
    if (path === "/dashboard") await expect(page.getByRole("progressbar", { name: /Application readiness:/ })).toBeVisible();
    if (path.startsWith("/professors/")) await expect(page.getByRole("article", { name: "Professor research profile" })).toBeVisible();
    if (path === "/profile") await expect(page.locator(".cv-analysis-panel")).not.toContainText("Loading your latest CV analysis…");
    await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });

    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.evaluate(() => window.scrollTo(0, 0));
      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(hasHorizontalOverflow).toBe(false);
      await page.screenshot({
        path: EVIDENCE_DIR + "/" + target.slug + "-" + viewport.name + ".png",
        fullPage: true,
      });
    }
    expect(runtimeErrors).toEqual([]);
  });
}
