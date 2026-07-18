import { describe, expect, it } from "vitest";

import { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog";
import { filterCatalog } from "./catalog-filter";

describe("filterCatalog", () => {
  it("combines institution, topic, and free-text filters", () => {
    const result = filterCatalog(LAB_CATALOG_FIXTURES, {
      institution: "Seoul National University",
      topic: "AI",
      query: "Vision",
    });

    expect(result.map((lab) => lab.id)).toEqual(["snu-demo-02"]);
  });

  it("matches professor and topic text without case sensitivity", () => {
    const professorResult = filterCatalog(LAB_CATALOG_FIXTURES, {
      institution: "",
      topic: "",
      query: "Demo Professor 20",
    });
    const topicResult = filterCatalog(LAB_CATALOG_FIXTURES, {
      institution: "",
      topic: "",
      query: "iot",
    });

    expect(professorResult.map((lab) => lab.id)).toEqual(["yonsei-demo-05"]);
    expect(topicResult.map((lab) => lab.id)).toEqual(["yonsei-demo-03"]);
  });
});
