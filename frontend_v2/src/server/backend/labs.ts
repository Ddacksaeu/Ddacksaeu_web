import { z } from "zod";

import { backendOrigin } from "./client";

export type LabSummary = Readonly<{ id: string; name: string; professorName: string; university: string; department: string; field: string; summary: string | null; keywords: readonly string[]; homepageUrl: string | null; updatedAt: string; recommendationScore: number | null; isFavorite: boolean }>;
export type LabFact = Readonly<{ factType: string; valueText: string | null; valueNumber: number | null; audience: string | null; origin: string; sourceUrl: string | null; sourceCheckedAt: string | null }>;
export type LabPaper = Readonly<{ id: string; title: string; venue: string; publishedYear: number; abstract: string | null; summary: string | null; keywords: readonly string[]; paperUrl: string | null; sourceUrl: string | null; sourceCheckedAt: string | null }>;
export type LabDetail = LabSummary & Readonly<{ location: string | null; contactEmail: string | null; sourceUrl: string | null; sourceCheckedAt: string | null; facts: readonly LabFact[]; papers: readonly LabPaper[] }>;
export type LabSearchResponse = Readonly<{ items: LabSummary[]; page: number; pageSize: number; total: number }>;

const labSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  professorName: z.string(),
  university: z.string(),
  department: z.string(),
  field: z.string(),
  summary: z.string().nullable(),
  keywords: z.array(z.string()),
  homepageUrl: z.string().nullable(),
  updatedAt: z.string(),
  recommendationScore: z.number().nullable(),
  isFavorite: z.boolean(),
});
const similarLabsSchema = z.object({ items: z.array(labSummarySchema) });

export async function fetchBackendLabs(query = ""): Promise<LabSearchResponse> {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  if (query.trim()) params.set("q", query.trim());
  const response = await fetch(`${backendOrigin()}/api/v1/labs?${params}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load labs");
  return response.json() as Promise<LabSearchResponse>;
}

export async function fetchBackendLab(id: string): Promise<LabDetail | null> {
  const response = await fetch(`${backendOrigin()}/api/v1/labs/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Unable to load lab");
  return response.json() as Promise<LabDetail>;
}

export async function fetchBackendSimilarLabs(id: string): Promise<readonly LabSummary[] | null> {
  try {
    const response = await fetch(`${backendOrigin()}/api/v1/labs/${encodeURIComponent(id)}/similar`, { cache: "no-store" });
    if (!response.ok) return null;
    return similarLabsSchema.parse(await response.json()).items;
  } catch (error) {
    if (error instanceof Error) return null;
    throw error;
  }
}
