import { z } from "zod";

const cvSummarySchema = z.object({
  id: z.string(),
  fileName: z.string(),
  contentType: z.string(),
  byteLength: z.number(),
}).readonly();

const profileSummarySchema = z.object({
  displayName: z.string(),
  researchInterests: z.array(z.string()).readonly(),
  preferredUniversity: z.string().default(""),
  applicationTerm: z.string().default(""),
  degreeProgram: z.string().default(""),
  consentedAt: z.string(),
}).readonly();

const profileWorkspaceSchema = z.object({
  profile: profileSummarySchema.nullable(),
  cvAssets: z.array(cvSummarySchema).readonly(),
  targetLabIds: z.array(z.string()).readonly().default([]),
  summary: z.object({
    savedProfessors: z.number(),
    contactDrafts: z.number(),
    schedules: z.number(),
  }).readonly().default({ savedProfessors: 0, contactDrafts: 0, schedules: 0 }),
}).readonly();

export type CvSummary = z.infer<typeof cvSummarySchema>;
export type ProfileSummary = z.infer<typeof profileSummarySchema>;
export type ProfileWorkspaceData = z.infer<typeof profileWorkspaceSchema>;

export type ProfileSubmission = {
  readonly displayName: string;
  readonly researchInterests: readonly string[];
  readonly preferredUniversity: string;
  readonly applicationTerm: string;
  readonly degreeProgram: string;
  readonly consentToStorage: boolean;
  readonly cvFile: File | null;
};
