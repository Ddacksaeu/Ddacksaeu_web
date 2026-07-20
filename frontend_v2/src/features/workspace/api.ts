import ky, { HTTPError } from "ky";
import { z } from "zod";

import { endDemoSession } from "../auth/demo-session";

const api = ky.create({ prefixUrl: "/api/backend", throwHttpErrors: true });
export type ApiState = "loading" | "ready" | "empty" | "unauthorized" | "error";

export class WorkspaceApiError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}

export async function request<T>(path: string, schema: z.ZodType<T>, options?: Parameters<typeof api>[1]): Promise<T> {
  try { return schema.parse(await api(path, options).json()); }
  catch (error) {
    if (error instanceof HTTPError) {
      if (error.response.status === 401 && typeof window !== "undefined") {
        endDemoSession(window.localStorage);
        window.location.replace("/login");
      }
      throw new WorkspaceApiError(error.response.status, `Request failed (${error.response.status}).`);
    }
    throw error;
  }
}

const profileSchema = z.object({ name: z.string(), affiliation: z.string(), status: z.string(), program: z.string(), interests: z.array(z.string()), skills: z.array(z.string()), methodologies: z.array(z.string()), projects: z.array(z.string()), updatedAt: z.string() });
const eventSchema = z.object({ id: z.string(), title: z.string(), kind: z.enum(["apply", "contact", "docs", "interview"]), date: z.string(), labId: z.string().nullable(), memo: z.string().nullable(), createdAt: z.string(), updatedAt: z.string() });
const admissionSchema = z.object({ id: z.string(), title: z.string(), eventType: z.string(), startAt: z.string(), endAt: z.string().nullable(), applicationUrl: z.string().nullable(), description: z.string().nullable(), isEstimated: z.boolean(), sourceUrl: z.string(), lastVerifiedAt: z.string().nullable(), isDeadlineImminent: z.boolean(), isEnded: z.boolean() });
const documentSchema = z.object({ original_filename: z.string().nullable(), keywords: z.array(z.string()), skills: z.array(z.string()), research_interests: z.array(z.string()), projects: z.array(z.object({ name: z.string(), description: z.string(), technologies: z.array(z.string()) })), short_summary: z.string() });
const recommendationSchema = z.object({ lab_id: z.string(), lab_name: z.string(), professor_name: z.string(), total_score: z.number(), short_reason: z.string(), matched_keywords: z.array(z.string()) }).transform((value) => ({ labId: value.lab_id, labName: value.lab_name, professorName: value.professor_name, totalScore: value.total_score, shortReason: value.short_reason, matchedKeywords: value.matched_keywords }));
const labSchema = z.object({ id: z.string(), name: z.string(), professorName: z.string(), department: z.string(), field: z.string(), contactEmail: z.string().nullable(), keywords: z.array(z.string()) });
const emailSchema = z.object({ labId: z.string(), subject: z.string(), body: z.string(), personalizationNotes: z.array(z.string()), generationMode: z.enum(["ai", "demo", "local_rule_based"]), model: z.string().nullable() });
const emailReviewSchema = z.object({ score: z.number(), summary: z.string(), issues: z.array(z.object({ category: z.enum(["spelling", "flow", "professor_fit"]), severity: z.enum(["info", "warning"]), message: z.string(), suggestion: z.string() })), reviewedSubject: z.string(), reviewedBody: z.string(), reviewMode: z.literal("local_rule_based") });

export type UserProfile = z.infer<typeof profileSchema>; export type CalendarEvent = z.infer<typeof eventSchema>; export type Admission = z.infer<typeof admissionSchema>; export type DocumentAnalysis = z.infer<typeof documentSchema>; export type Recommendation = z.infer<typeof recommendationSchema>; export type Lab = z.infer<typeof labSchema>; export type EmailDraft = z.infer<typeof emailSchema>; export type EmailReview = z.infer<typeof emailReviewSchema>;
export const getProfile = () => request("me/profile", profileSchema);
export const saveProfile = (value: Partial<UserProfile>) => request("me/profile", profileSchema, { method: "PATCH", json: value });
export const getEvents = () => request("me/calendar-events", z.object({ items: z.array(eventSchema) })).then((value) => value.items);
export const createEvent = (value: Pick<CalendarEvent, "title" | "kind" | "date" | "labId" | "memo">) => request("me/calendar-events", eventSchema, { method: "POST", json: value });
export const updateEvent = (id: string, value: Partial<Pick<CalendarEvent, "title" | "kind" | "date" | "labId" | "memo">>) => request(`me/calendar-events/${id}`, eventSchema, { method: "PATCH", json: value });
export const deleteEvent = (id: string) => api.delete(`me/calendar-events/${id}`);
export const getAdmissions = () => request("admissions", z.object({ items: z.array(admissionSchema) })).then((value) => value.items);
export const getLatestAnalysis = () => request("documents/latest", documentSchema);
export const getRecommendations = () => request("recommendations", z.object({ items: z.array(recommendationSchema) })).then((value) => value.items);
export const getFavorites = () => request("me/favorites", z.object({ labIds: z.array(z.string()) })).then((value) => value.labIds);
export const getLab = (id: string) => request(`labs/${id}`, labSchema);
export const createEmailDraft = (labId: string) => request("email/draft", emailSchema, { method: "POST", json: { labId, language: "en", tone: "polite", length: "standard", purpose: "graduate_application" } });
export const reviewEmailDraft = (labId: string, subject: string, body: string) => request("email/review", emailReviewSchema, { method: "POST", json: { labId, subject, body, language: /[가-힣]/.test(body) ? "ko" : "en" } });
