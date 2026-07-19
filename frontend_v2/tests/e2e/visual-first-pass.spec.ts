import { expect, test } from "@playwright/test";

import { useSignedInBeforeOnboarding, useSignedInDemo } from "./demo-session";

const PAGES = [
  { slug: "landing", path: "/", heading: "Find professors who match your" },
  { slug: "login", path: "/login", heading: "Graduate school planning," },
  { slug: "onboarding", path: "/onboarding", heading: "Tell us what you are looking for" },
  { slug: "dashboard", path: "/dashboard", heading: "Home" },
  { slug: "professors", path: "/professors", heading: "Find professors aligned with your research" },
  { slug: "professor-detail", path: "/professors/snu-demo-02", heading: "Intelligent Vision Lab" },
  { slug: "cv", path: "/cv", heading: "CV and portfolio analysis" },
  { slug: "contact", path: "/contact", heading: "Outreach email draft" },
  { slug: "calendar", path: "/calendar", heading: "See admissions deadlines" },
  { slug: "profile", path: "/profile", heading: "research profile" },
] as const;

const VIEWPORTS = [
  { name: "desktop", width: 1280, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 375, height: 812 },
] as const;

for (const target of PAGES) {
  test(target.slug + " renders at all product breakpoints", async ({ page }) => {
    if (target.path !== "/" && target.path !== "/login") {
      await (target.path === "/onboarding" ? useSignedInBeforeOnboarding(page) : useSignedInDemo(page));
    }
    await page.goto(target.path);
    await expect(page.getByRole("heading", { name: new RegExp(target.heading), level: 1 })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/\bDemo\b|\(Demo\)|fictional|product testing|not real recruitment/i);
    if (target.path === "/dashboard") await expect(page.getByText("Next: create a research profile")).toBeVisible();
    if (target.path.startsWith("/professors/")) await expect(page.getByText("Create a profile to compare", { exact: true })).toBeVisible();
    await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });

    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.evaluate(() => window.scrollTo(0, 0));
      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(hasHorizontalOverflow).toBe(false);
      await page.screenshot({
        path: ".omo/evidence/dashboard-redesign/" + target.slug + "-" + viewport.name + ".png",
        fullPage: true,
      });
    }
  });
}
