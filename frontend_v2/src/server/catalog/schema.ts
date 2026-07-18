import { z } from "zod";

const APPROVED_CATALOG_HOSTS = new Set([
  "www.snu.ac.kr",
  "cse.snu.ac.kr",
  "www.kaist.ac.kr",
  "cs.kaist.ac.kr",
  "www.postech.ac.kr",
  "cse.postech.ac.kr",
  "www.yonsei.ac.kr",
  "cs.yonsei.ac.kr",
]);

const approvedCatalogUrlSchema = z.url().refine((value) => {
  if (!URL.canParse(value)) return false;
  const url = new URL(value);
  return url.protocol === "https:" && APPROVED_CATALOG_HOSTS.has(url.hostname);
}, "Expected an approved official HTTPS URL");

export const LabCatalogEntrySchema = z.strictObject({
  id: z.string().regex(/^[a-z]+-demo-\d{2}$/),
  dataStatus: z.literal("demo"),
  labName: z.string().endsWith("(Demo)"),
  professor: z.string().endsWith("(Demo)"),
  institution: z.string().min(1),
  topics: z.array(z.string().min(1)).min(1).readonly(),
  labUrl: approvedCatalogUrlSchema,
  officialSourceUrl: approvedCatalogUrlSchema,
  verifiedAt: z.iso.datetime({ offset: true }),
}).readonly();

export const LabCatalogSchema = z.array(LabCatalogEntrySchema).readonly();
export type LabCatalogEntry = z.infer<typeof LabCatalogEntrySchema>;
