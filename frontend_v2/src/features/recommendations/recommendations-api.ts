import ky from "ky";
import { z } from "zod";

const scorePartSchema = z.object({
  score: z.number(),
  max_score: z.number(),
  raw_score: z.number(),
  available: z.boolean(),
});

const evidenceSchema = z.object({
  type: z.string(),
  text: z.string(),
});

const recommendationSchema = z.object({
  lab_id: z.string(),
  lab_name: z.string(),
  professor_name: z.string(),
  university: z.string(),
  department: z.string(),
  total_score: z.number().min(0).max(100),
  matched_keywords: z.array(z.string()),
  missing_keywords: z.array(z.string()),
  score_breakdown: z.record(z.string(), scorePartSchema),
  evidence: z.array(evidenceSchema),
  short_reason: z.string(),
  recommended_action: z.string(),
  data_completeness: z.number().min(0).max(1),
  warnings: z.array(z.string()),
  data_origin: z.string(),
  calculated_at: z.string(),
});

const recommendationResponseSchema = z.object({
  items: z.array(recommendationSchema),
});

export type RecommendationScorePart = Readonly<{
  score: number;
  maxScore: number;
  rawScore: number;
  available: boolean;
}>;

export type Recommendation = Readonly<{
  labId: string;
  labName: string;
  professorName: string;
  university: string;
  department: string;
  totalScore: number;
  matchedKeywords: readonly string[];
  missingKeywords: readonly string[];
  scoreBreakdown: Readonly<Record<string, RecommendationScorePart>>;
  evidence: readonly Readonly<{ type: string; text: string }>[];
  shortReason: string;
  recommendedAction: string;
  dataCompleteness: number;
  warnings: readonly string[];
  dataOrigin: string;
  calculatedAt: string;
}>;

export function parseRecommendationResponse(input: unknown): readonly Recommendation[] {
  const parsed = recommendationResponseSchema.parse(input);

  return parsed.items.map((item) => {
    const scoreBreakdown: Record<string, RecommendationScorePart> = {};
    for (const [name, part] of Object.entries(item.score_breakdown)) {
      scoreBreakdown[name] = {
        score: part.score,
        maxScore: part.max_score,
        rawScore: part.raw_score,
        available: part.available,
      };
    }

    return {
      labId: item.lab_id,
      labName: item.lab_name,
      professorName: item.professor_name,
      university: item.university,
      department: item.department,
      totalScore: item.total_score,
      matchedKeywords: item.matched_keywords,
      missingKeywords: item.missing_keywords,
      scoreBreakdown,
      evidence: item.evidence,
      shortReason: item.short_reason,
      recommendedAction: item.recommended_action,
      dataCompleteness: item.data_completeness,
      warnings: item.warnings,
      dataOrigin: item.data_origin,
      calculatedAt: item.calculated_at,
    };
  });
}

export async function getRecommendations(): Promise<readonly Recommendation[]> {
  const response: unknown = await ky.get("/api/backend/recommendations").json();
  return parseRecommendationResponse(response);
}
