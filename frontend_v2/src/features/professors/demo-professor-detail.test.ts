import { describe, expect, it } from "vitest";

import { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog";
import { createDemoProfessorDetail } from "./demo-professor-detail";

describe("createDemoProfessorDetail", () => {
  it("builds a dense, source-aware detail model", () => {
    const professor = LAB_CATALOG_FIXTURES[0];
    if (professor === undefined) throw new TypeError("Expected a catalog fixture");

    const detail = createDemoProfessorDetail(professor);

    expect(detail.researchFocus).toHaveLength(3);
    expect(detail.papers).toHaveLength(4);
    expect(detail.methods.length).toBeGreaterThanOrEqual(5);
    expect(detail.recruitmentNote).toContain("unverified");
    expect(detail.sourceNote).toContain("crawler integration");
  });

  it("uses a safe fallback when only one topic exists", () => {
    const professor = LAB_CATALOG_FIXTURES[0];
    if (professor === undefined) throw new TypeError("Expected a catalog fixture");

    const detail = createDemoProfessorDetail({ ...professor, topics: ["AI"] });

    expect(detail.researchFocus[1]?.title).toContain("Applied research");
  });
});
