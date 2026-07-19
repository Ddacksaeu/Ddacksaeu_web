import { describe, expect, it } from "vitest";

import { parseRecommendationResponse } from "./recommendations-api";

describe("parseRecommendationResponse", () => {
  it("converts the backend recommendation contract without changing rank order", () => {
    // Given
    const response = {
      items: [
        {
          lab_id: "lab-vision",
          lab_name: "Vision Intelligence Lab",
          professor_name: "Mina Park",
          university: "POSTECH",
          department: "Computer Science",
          total_score: 91.4,
          matched_keywords: ["Computer Vision", "PyTorch"],
          missing_keywords: ["Multimodal Learning"],
          score_breakdown: {
            keyword_overlap: {
              score: 38,
              max_score: 40,
              raw_score: 0.95,
              available: true,
            },
          },
          evidence: [{ type: "keyword", text: "Computer Vision appears in the CV." }],
          short_reason: "Your vision experience closely matches this lab.",
          recommended_action: "Mention the PyTorch reproduction project.",
          data_completeness: 0.9,
          warnings: [],
          data_origin: "server_recommendation",
          calculated_at: "2026-07-19T09:00:00Z",
        },
      ],
    };

    // When
    const recommendations = parseRecommendationResponse(response);

    // Then
    expect(recommendations).toHaveLength(1);
    expect(recommendations[0]).toMatchObject({
      labId: "lab-vision",
      labName: "Vision Intelligence Lab",
      professorName: "Mina Park",
      university: "POSTECH",
      department: "Computer Science",
      totalScore: 91.4,
      matchedKeywords: ["Computer Vision", "PyTorch"],
      shortReason: "Your vision experience closely matches this lab.",
    });
    expect(recommendations[0]?.scoreBreakdown.keyword_overlap).toEqual({
      score: 38,
      maxScore: 40,
      rawScore: 0.95,
      available: true,
    });
  });
});
