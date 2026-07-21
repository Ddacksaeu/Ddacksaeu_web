import ky, { HTTPError } from "ky";
import { z } from "zod";

import { endDemoSession } from "../auth/demo-session";

const api = ky.create({ credentials: "same-origin", prefixUrl: "/api/backend", throwHttpErrors: true });

export class WorkspaceApiError extends Error {
  constructor(readonly status: number, message: string) { super(message); this.name = "WorkspaceApiError"; }
}

function messageForStatus(status: number, code?: string): string {
  if (status === 0 || code === "backend_unavailable") return "Could not connect to the server. Check that the backend is running.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You do not have permission to access this resource.";
  if (status === 404) return "The requested resource could not be found.";
  if (status === 409) return "This action requires additional profile or CV information.";
  if (status === 413) return "The selected file exceeds the 10 MB limit.";
  if (status === 422) return "Please check the information and try again.";
  if (status >= 500) return "The server could not process this request.";
  return "The request could not be completed.";
}

async function errorCode(response: Response): Promise<string | undefined> {
  try {
    const body: unknown = await response.clone().json();
    if (typeof body !== "object" || body === null || !("error" in body)) return undefined;
    const error = body.error;
    return typeof error === "object" && error !== null && "code" in error && typeof error.code === "string" ? error.code : undefined;
  } catch { return undefined; }
}

async function request<T>(path: string, schema: z.ZodType<T>, options?: Parameters<typeof api>[1]): Promise<T> {
  try { return schema.parse(await api(path, options).json()); }
  catch (error) {
    if (error instanceof HTTPError) {
      if (error.response.status === 401 && typeof window !== "undefined") {
        endDemoSession(window.localStorage);
        window.location.replace("/login");
      }
      throw new WorkspaceApiError(error.response.status, messageForStatus(error.response.status, await errorCode(error.response)));
    }
    if (error instanceof WorkspaceApiError) throw error;
    throw new WorkspaceApiError(0, messageForStatus(0));
  }
}

async function requestEmpty(path: string, options?: Parameters<typeof api>[1]): Promise<void> {
  try { await api(path, options); }
  catch (error) {
    if (error instanceof HTTPError) {
      if (error.response.status === 401 && typeof window !== "undefined") {
        endDemoSession(window.localStorage);
        window.location.replace("/login");
      }
      throw new WorkspaceApiError(error.response.status, messageForStatus(error.response.status, await errorCode(error.response)));
    }
    throw new WorkspaceApiError(0, messageForStatus(0));
  }
}

const profileSchema = z.object({ name: z.string(), affiliation: z.string(), status: z.string(), program: z.string(), interests: z.array(z.string()), skills: z.array(z.string()), methodologies: z.array(z.string()), projects: z.array(z.string()), updatedAt: z.string() });
const eventSchema = z.object({ id: z.string(), title: z.string(), kind: z.enum(["apply", "contact", "docs", "interview"]), date: z.string(), labId: z.string().nullable(), memo: z.string().nullable(), createdAt: z.string(), updatedAt: z.string() });
const admissionSchema = z.object({
  id: z.string(),
  title: z.string(),
  event_type: z.string(),
  start_at: z.string(),
  end_at: z.string().nullable(),
  application_url: z.string().nullable(),
  description: z.string().nullable(),
  is_estimated: z.boolean(),
  source_url: z.string(),
  last_verified_at: z.string().nullable(),
  is_deadline_imminent: z.boolean(),
  is_ended: z.boolean(),
}).transform((value) => ({
  id: value.id,
  title: value.title,
  eventType: value.event_type,
  startAt: value.start_at,
  endAt: value.end_at,
  applicationUrl: value.application_url,
  description: value.description,
  isEstimated: value.is_estimated,
  sourceUrl: value.source_url,
  lastVerifiedAt: value.last_verified_at,
  isDeadlineImminent: value.is_deadline_imminent,
  isEnded: value.is_ended,
}));
const documentSchema = z.object({ original_filename: z.string().nullable(), keywords: z.array(z.string()), skills: z.array(z.string()), research_interests: z.array(z.string()), projects: z.array(z.object({ name: z.string(), description: z.string(), technologies: z.array(z.string()) })), short_summary: z.string() });
const recommendationSchema = z.object({ lab_id: z.string(), lab_name: z.string(), professor_name: z.string(), total_score: z.number(), short_reason: z.string(), matched_keywords: z.array(z.string()) }).transform((value) => ({ labId: value.lab_id, labName: value.lab_name, professorName: value.professor_name, totalScore: value.total_score, shortReason: value.short_reason, matchedKeywords: value.matched_keywords }));
const labSchema = z.object({ id: z.string(), name: z.string(), professorName: z.string(), department: z.string(), field: z.string(), contactEmail: z.string().nullable(), keywords: z.array(z.string()) });
const emailSchema = z.object({ labId: z.string(), subject: z.string(), body: z.string(), personalizationNotes: z.array(z.string()), generationMode: z.enum(["ai", "demo", "local_rule_based"]), model: z.string().nullable() });
const emailReviewSchema = z.object({ score: z.number(), summary: z.string(), issues: z.array(z.object({ category: z.enum(["spelling", "flow", "professor_fit"]), severity: z.enum(["info", "warning"]), message: z.string(), suggestion: z.string() })), reviewedSubject: z.string(), reviewedBody: z.string(), reviewMode: z.literal("local_rule_based") });

export type UserProfile = z.infer<typeof profileSchema>; export type CalendarEvent = z.infer<typeof eventSchema>; export type Admission = z.infer<typeof admissionSchema>; export type DocumentAnalysis = z.infer<typeof documentSchema>; export type Recommendation = z.infer<typeof recommendationSchema>; export type Lab = z.infer<typeof labSchema>; export type EmailReview = z.infer<typeof emailReviewSchema>;
export const getProfile = () => request("me/profile", profileSchema);
export const saveProfile = (value: Partial<UserProfile>) => request("me/profile", profileSchema, { method: "PATCH", json: value });
export const getEvents = () => request("me/calendar-events", z.object({ items: z.array(eventSchema) })).then((value) => value.items);
export const createEvent = (value: Pick<CalendarEvent, "title" | "kind" | "date" | "labId" | "memo">) => request("me/calendar-events", eventSchema, { method: "POST", json: value });
export const updateEvent = (id: string, value: Partial<Pick<CalendarEvent, "title" | "kind" | "date" | "labId" | "memo">>) => request(`me/calendar-events/${id}`, eventSchema, { method: "PATCH", json: value });
export const deleteEvent = (id: string) => requestEmpty(`me/calendar-events/${id}`, { method: "DELETE" });
export const getAdmissions = () => request("admissions", z.object({ items: z.array(admissionSchema) })).then((value) => value.items);
export const getLatestAnalysis = () => request("documents/latest", documentSchema);
export const getRecommendations = () => request("recommendations", z.object({ items: z.array(recommendationSchema) })).then((value) => value.items);
export const getFavorites = () => request("me/favorites", z.object({ labIds: z.array(z.string()) })).then((value) => value.labIds);
export const getLab = (id: string) => request(`labs/${id}`, labSchema);
export const createEmailDraft = (labId: string) => request("email/draft", emailSchema, { method: "POST", json: { labId, language: "en", tone: "polite", length: "standard", purpose: "graduate_application" } });
export const reviewEmailDraft = (labId: string, subject: string, body: string) => request("email/review", emailReviewSchema, { method: "POST", json: { labId, subject, body, language: /[가-힣]/.test(body) ? "ko" : "en" } });
