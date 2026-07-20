import { expect, test, type Page } from "@playwright/test";

import { useSignedInDemo } from "./demo-session";

const analysis = {
  document_id: "document-1",
  analysis_id: "analysis-1",
  status: "completed",
  analyzer_origin: "local_rule_based",
  original_filename: "research-cv.pdf",
  file_type: "pdf",
  file_size: 145_000,
  warnings: [],
  education: ["B.S. Computer Science"],
  skills: ["PyTorch", "Python"],
  projects: [{ name: "Vision project", description: "Built an image classifier.", technologies: ["PyTorch"] }],
  research_experience: ["Computer vision reproduction study"],
  research_interests: ["Computer Vision", "Multimodal Learning"],
  strengths: ["Reproducible experiments"],
  missing_information: [],
  keywords: ["Computer Vision", "PyTorch"],
  keyword_weights: { "Computer Vision": 1, PyTorch: 0.8 },
  short_summary: "Computer vision researcher with hands-on PyTorch experience.",
  evidence_items: {},
};

const recommendations = {
  items: [{
    lab_id: "lab-vision",
    lab_name: "Vision Intelligence Lab",
    professor_name: "Mina Park",
    university: "POSTECH",
    department: "Computer Science",
    total_score: 91.4,
    matched_keywords: ["Computer Vision", "PyTorch"],
    missing_keywords: ["Multimodal Learning"],
    score_breakdown: {
      keyword_overlap: { score: 38, max_score: 40, raw_score: 0.95, available: true },
    },
    evidence: [{ type: "keyword", text: "Computer Vision appears in the CV." }],
    short_reason: "Your vision experience closely matches this lab.",
    recommended_action: "Mention the PyTorch reproduction project.",
    data_completeness: 0.9,
    warnings: [],
    data_origin: "server_recommendation",
    calculated_at: "2026-07-19T09:00:00Z",
  }],
};

async function mockCvResults(page: Page) {
  await page.route("**/api/backend/documents/latest", async (route) => {
    await route.fulfill({ json: analysis });
  });
  await page.route("**/api/backend/documents", async (route) => {
    await route.fulfill({ json: [analysis] });
  });
  await page.route("**/api/backend/recommendations", async (route) => {
    await route.fulfill({ json: recommendations });
  });
}

test("CV analysis shows the highest-fit professor and its matching basis", async ({ page }) => {
  await useSignedInDemo(page);
  await mockCvResults(page);
  await page.goto("/cv");

  const matches = page.getByRole("region", { name: "CV-based professor recommendations" });
  await expect(matches).toBeVisible();
  await expect(matches.getByRole("heading", { name: "Best professor matches" })).toBeVisible();
  await expect(matches.getByText("#1 Best match · 91.4 research match")).toBeVisible();
  await expect(matches.getByRole("heading", { name: "Vision Intelligence Lab" })).toBeVisible();
  await expect(matches.getByText("Computer Vision, PyTorch")).toBeVisible();
  await expect(matches.getByRole("link", { name: "View professor details" })).toHaveAttribute(
    "href",
    "/professors/lab-vision",
  );
  await expect(page.getByLabel("Application goal")).toHaveCount(0);
});

test("a prior CV analysis can be selected from its history", async ({ page }) => {
  const olderAnalysis = {
    ...analysis,
    analysis_id: "analysis-older",
    original_filename: "older-cv.txt",
    short_summary: "Earlier systems research experience.",
  };
  await useSignedInDemo(page);
  await page.route("**/api/backend/documents/latest", async (route) => {
    await route.fulfill({ json: analysis });
  });
  await page.route("**/api/backend/documents", async (route) => {
    await route.fulfill({ json: [analysis, olderAnalysis] });
  });
  await page.route("**/api/backend/recommendations", async (route) => {
    await route.fulfill({ json: recommendations });
  });

  await page.goto("/cv");
  const olderEntry = page.locator(".cv-history button").filter({ hasText: "older-cv.txt" });
  await expect(olderEntry).toHaveCount(1);
  await olderEntry.click();

  await expect(page.getByRole("heading", { name: "older-cv.txt" })).toBeVisible();
  await expect(olderEntry).toHaveAttribute("aria-pressed", "true");
});

test("CV professor matches remain readable across product breakpoints", async ({ page }) => {
  await useSignedInDemo(page);
  await mockCvResults(page);
  await page.goto("/cv");
  await expect(page.getByRole("region", { name: "CV-based professor recommendations" })).toBeVisible();

  for (const viewport of [
    { width: 1280, height: 900 },
    { width: 768, height: 1024 },
    { width: 375, height: 812 },
  ]) {
    await page.setViewportSize(viewport);
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
    await page.screenshot({
      path: ".omo/evidence/cv-professor-match/cv-" + viewport.width + ".png",
      fullPage: true,
    });
  }
});
