import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "./client";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type LabListItem = {
  id: string;
  name: string;
  professorName: string;
  university: string;
  department: string;
  field: string;
  summary: string | null;
  keywords: string[];
  homepageUrl: string | null;
  updatedAt: string;
  recommendationScore: number | null;
  isFavorite: boolean;
};

export type LabFact = {
  factType: string;
  valueText: string | null;
  valueNumber: number | null;
  audience: string | null;
  origin: string;
  sourceUrl: string | null;
  sourceCheckedAt: string | null;
};

export type LabPaper = {
  id: string;
  title: string;
  venue: string;
  publishedYear: number;
  abstract: string | null;
  summary: string | null;
  keywords: string[];
  paperUrl: string | null;
  sourceUrl: string | null;
  sourceCheckedAt: string | null;
};

export type LabDetail = LabListItem & {
  location: string | null;
  contactEmail: string | null;
  sourceUrl: string | null;
  sourceCheckedAt: string | null;
  facts: LabFact[];
  papers: LabPaper[];
};

export type LabSearchParams = {
  q?: string;
  department?: string;
  fields?: string[];
  sort?: "score" | "recent";
  page?: number;
  pageSize?: number;
};

export type LabSearchResponse = {
  items: LabListItem[];
  page: number;
  pageSize: number;
  total: number;
};

async function request<T>(path: string): Promise<T> {
  const response = await apiFetch(path);
  if (!response.ok) {
    throw new ApiError("Unable to load lab data.", response.status);
  }
  return response.json() as Promise<T>;
}

export async function getLabs(params: LabSearchParams = {}): Promise<LabSearchResponse> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.department) query.set("department", params.department);
  params.fields?.forEach((field) => query.append("field", field));
  query.set("sort", params.sort ?? "recent");
  query.set("page", String(params.page ?? 1));
  query.set("page_size", String(params.pageSize ?? 20));
  return request<LabSearchResponse>(`/labs?${query.toString()}`);
}

export async function getLab(labId: string): Promise<LabDetail> {
  return request<LabDetail>(`/labs/${encodeURIComponent(labId)}`);
}

export async function getSimilarLabs(labId: string): Promise<LabListItem[]> {
  const response = await request<{ items: LabListItem[] }>(
    `/labs/${encodeURIComponent(labId)}/similar?limit=3`,
  );
  return response.items;
}

export const labsQueryOptions = (params: LabSearchParams) =>
  queryOptions({ queryKey: ["labs", params], queryFn: () => getLabs(params) });

export const labQueryOptions = (labId: string) =>
  queryOptions({ queryKey: ["labs", labId], queryFn: () => getLab(labId) });

export const similarLabsQueryOptions = (labId: string) =>
  queryOptions({ queryKey: ["labs", labId, "similar"], queryFn: () => getSimilarLabs(labId) });
