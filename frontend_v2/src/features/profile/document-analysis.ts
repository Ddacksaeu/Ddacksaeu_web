import { z } from "zod";

const evidenceItemSchema = z.object({
  value: z.string(),
  confidence: z.number().min(0).max(1),
  evidence: z.string(),
}).readonly();

const projectSchema = z.object({
  name: z.string(),
  description: z.string(),
  technologies: z.array(z.string()).readonly(),
}).readonly();

export const documentAnalysisSchema = z.object({
  document_id: z.string(),
  analysis_id: z.string(),
  status: z.string(),
  analyzer_origin: z.string(),
  original_filename: z.string().nullable(),
  file_type: z.string().nullable(),
  file_size: z.number().nullable(),
  warnings: z.array(z.string()).readonly(),
  education: z.array(z.string()).readonly(),
  skills: z.array(z.string()).readonly(),
  projects: z.array(projectSchema).readonly(),
  research_experience: z.array(z.string()).readonly(),
  research_interests: z.array(z.string()).readonly(),
  strengths: z.array(z.string()).readonly(),
  missing_information: z.array(z.string()).readonly(),
  keywords: z.array(z.string()).readonly(),
  keyword_weights: z.record(z.string(), z.number()).readonly(),
  short_summary: z.string(),
  evidence_items: z.record(z.string(), z.array(evidenceItemSchema).readonly()).readonly(),
}).readonly();

export type DocumentAnalysis = z.infer<typeof documentAnalysisSchema>;
export type EvidenceItem = z.infer<typeof evidenceItemSchema>;
