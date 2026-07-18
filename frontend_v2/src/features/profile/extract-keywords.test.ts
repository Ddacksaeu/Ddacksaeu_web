import { describe, expect, it } from "vitest";

import { extractResearchKeywords } from "./extract-keywords";

describe("extractResearchKeywords", () => {
  it("extracts normalized research topics from statement text", () => {
    expect(extractResearchKeywords("I completed Computer Vision, HCI, and Machine Learning projects."))
      .toEqual(["Computer Vision", "HCI", "Machine Learning"]);
  });

  it("returns no invented keyword when the text has no known topic", () => {
    expect(extractResearchKeywords("I am preparing for graduate school.")).toEqual([]);
  });
});
