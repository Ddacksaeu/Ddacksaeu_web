const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(
  /\/$/,
  "",
);

export class RecommendationApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "RecommendationApiError";
  }
}

export type DocumentAnalysis = {
  document_id: string;
  analysis_id: string;
  status: "completed";
  skills: string[];
  projects: { name: string; description: string; technologies: string[] }[];
  research_interests: string[];
  keywords: string[];
  short_summary: string;
  missing_information: string[];
};

export type Recommendation = {
  lab_id: string;
  lab_name: string;
  professor_name: string;
  university: string;
  department: string;
  total_score: number;
  confidence: number;
  matched_keywords: string[];
  missing_keywords: string[];
  score_breakdown: Record<string, { score: number; contribution: number; unavailable: boolean }>;
  short_reason: string;
  recommended_action: string;
};

async function parseError(response: Response) {
  const payload = (await response.json().catch(() => null)) as {
    error?: { message?: string };
  } | null;
  return payload?.error?.message ?? "The request could not be completed.";
}

export async function analyzeDocument(file: File, userId = "demo-user"): Promise<DocumentAnalysis> {
  const form = new FormData();
  form.set("file", file);
  form.set("user_id", userId);
  const response = await fetch(`${API_BASE_URL}/documents/analyze`, { method: "POST", body: form });
  if (!response.ok) throw new RecommendationApiError(await parseError(response), response.status);
  return response.json() as Promise<DocumentAnalysis>;
}

export async function recomputeRecommendations(userId = "demo-user"): Promise<Recommendation[]> {
  const response = await fetch(
    `${API_BASE_URL}/recommendations/recompute?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
  if (!response.ok) throw new RecommendationApiError(await parseError(response), response.status);
  const payload = (await response.json()) as { items: Recommendation[] };
  return payload.items;
}
