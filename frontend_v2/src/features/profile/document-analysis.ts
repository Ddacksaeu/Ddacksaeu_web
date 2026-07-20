import { z } from "zod";

const evidenceItemSchema = z.object({
  value: z.string(),
  confidence: z.number().min(0).max(1),
  evidence: z.string(),
}).readonly();

const projectSchema = z.object({
  name: z.string(),
  organization: z.string().default(""),
  location: z.string().default(""),
  start_date: z.string().default(""),
  end_date: z.string().default(""),
  description: z.string(),
  details: z.array(z.string()).readonly().default([]),
  technologies: z.array(z.string()).readonly(),
}).readonly();

const educationObjectSchema = z.object({
  degree: z.string(),
  institution: z.string(),
  location: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  details: z.array(z.string()).readonly(),
}).readonly();
const educationSchema = z.union([educationObjectSchema, z.string().transform((degree) => ({ degree, institution: "", location: "", start_date: "", end_date: "", details: [] as readonly string[] }))]);

const experienceObjectSchema = z.object({
  title: z.string(),
  organization: z.string(),
  location: z.string(),
  start_date: z.string(),
  end_date: z.string(),
  details: z.array(z.string()).readonly(),
}).readonly();
const experienceSchema = z.union([experienceObjectSchema, z.string().transform((title) => ({ title, organization: "", location: "", start_date: "", end_date: "", details: [] as readonly string[] }))]);

const categoryFeedbackSchema = z.object({
  category: z.string(),
  current_state: z.string(),
  improvements: z.array(z.string()).readonly(),
  suggestions: z.array(z.string()).readonly(),
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
  education: z.array(educationSchema).readonly(),
  work_experience: z.array(experienceSchema).readonly().default([]),
  campus_community_involvement: z.array(experienceSchema).readonly().default([]),
  skills: z.array(z.string()).readonly(),
  projects: z.array(projectSchema).readonly(),
  research_experience: z.array(experienceSchema).readonly(),
  research_interests: z.array(z.string()).readonly(),
  strengths: z.array(z.string()).readonly(),
  missing_information: z.array(z.string()).readonly(),
  keywords: z.array(z.string()).readonly(),
  keyword_weights: z.record(z.string(), z.number()).readonly(),
  short_summary: z.string(),
  evidence_items: z.record(z.string(), z.array(evidenceItemSchema).readonly()).readonly(),
  category_feedback: z.array(categoryFeedbackSchema).readonly().default([]),
}).readonly();

export type DocumentAnalysis = z.infer<typeof documentAnalysisSchema>;
export type EvidenceItem = z.infer<typeof evidenceItemSchema>;
export type CategoryFeedback = z.infer<typeof categoryFeedbackSchema>;
