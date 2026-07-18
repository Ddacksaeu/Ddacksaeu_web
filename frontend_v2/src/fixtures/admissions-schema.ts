import { z } from "zod";

export const AdmissionScheduleSchema = z.object({
  id: z.string().regex(/^admission-demo-\d{2}$/),
  dataStatus: z.literal("demo"),
  institution: z.string().min(1),
  lab: z.string().min(1),
  stage: z.enum(["Application opens", "Document review", "Interview", "Decision"]),
  date: z.iso.date(),
  timezone: z.literal("Asia/Seoul"),
  sourceLabel: z.literal("Official admissions website"),
  officialSourceUrl: z.url(),
  scheduleNote: z.literal("Fictional schedule for the hackathon demo"),
});

export type AdmissionSchedule = z.infer<typeof AdmissionScheduleSchema>;
