import { describe, expect, it } from "vitest";

import { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog";
import { matchLabsByTopics } from "./match-labs";

describe("matchLabsByTopics", () => {
  it("ranks labs by the number of overlapping topics", () => {
    // Given
    const keywords = ["AI", "Systems"];

    // When
    const recommendations = matchLabsByTopics(LAB_CATALOG_FIXTURES, keywords);

    // Then
    expect(recommendations[0]?.lab.id).toBe("snu-demo-01");
    expect(recommendations[0]?.matchingTopics).toEqual(["AI", "Systems"]);
  });

  it("matches keywords without case or surrounding-space differences", () => {
    // Given
    const keywords = ["  hci  "];

    // When
    const recommendations = matchLabsByTopics(LAB_CATALOG_FIXTURES, keywords);

    // Then
    expect(recommendations.map(({ lab }) => lab.id)).toEqual([
      "snu-demo-03",
      "kaist-demo-05",
    ]);
  });

  it("returns no recommendation when no topic overlaps", () => {
    // Given
    const keywords = ["Quantum Biology"];

    // When
    const recommendations = matchLabsByTopics(LAB_CATALOG_FIXTURES, keywords);

    // Then
    expect(recommendations).toEqual([]);
  });

  it("returns no recommendation before a keyword is entered", () => {
    // Given
    const keywords: readonly string[] = [];

    // When
    const recommendations = matchLabsByTopics(LAB_CATALOG_FIXTURES, keywords);

    // Then
    expect(recommendations).toEqual([]);
  });

  it("limits the ranked recommendations", () => {
    // Given
    const keywords = ["HCI"];

    // When
    const recommendations = matchLabsByTopics(LAB_CATALOG_FIXTURES, keywords, 1);

    // Then
    expect(recommendations.map(({ lab }) => lab.id)).toEqual(["snu-demo-03"]);
  });
});
