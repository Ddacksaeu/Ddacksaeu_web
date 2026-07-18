import type { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog";

type DemoLab = (typeof LAB_CATALOG_FIXTURES)[number];

export type LabRecommendation = {
  readonly lab: DemoLab;
  readonly matchingTopics: readonly string[];
};

export function matchLabsByTopics(
  labs: readonly DemoLab[],
  keywords: readonly string[],
  limit = 3,
): readonly LabRecommendation[] {
  const normalizedKeywords = new Set(
    keywords.flatMap((keyword) => {
      const normalized = keyword.trim().toLocaleLowerCase();
      return normalized.length > 0 ? [normalized] : [];
    }),
  );

  return labs
    .flatMap((lab) => {
      const matchingTopics = lab.topics.filter((topic) =>
        normalizedKeywords.has(topic.toLocaleLowerCase()),
      );
      return matchingTopics.length > 0 ? [{ lab, matchingTopics }] : [];
    })
    .sort((left, right) => right.matchingTopics.length - left.matchingTopics.length)
    .slice(0, Math.max(0, limit));
}
