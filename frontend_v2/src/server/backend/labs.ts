import type { LabCatalogEntry } from "../catalog/schema";
import { backendOrigin } from "./client";

type ApiLab = { id: string; name: string; professorName: string; university: string; keywords: string[]; homepageUrl: string | null; sourceUrl?: string | null; updatedAt: string };

function toCatalogLab(lab: ApiLab): LabCatalogEntry {
  const source = lab.homepageUrl ?? lab.sourceUrl ?? "https://www.postech.ac.kr";
  return { id: lab.id, dataStatus: "demo", labName: `${lab.name} (Demo)`, professor: `${lab.professorName} (Demo)`, institution: lab.university, topics: lab.keywords, labUrl: source, officialSourceUrl: source, verifiedAt: lab.updatedAt } as unknown as LabCatalogEntry;
}

export async function fetchBackendLabs(): Promise<readonly LabCatalogEntry[]> {
  const response = await fetch(`${backendOrigin()}/api/v1/labs`, { cache: "no-store" });
  if (!response.ok) return [];
  const body = await response.json() as { items: ApiLab[] };
  return body.items.map(toCatalogLab);
}

export async function fetchBackendLab(id: string): Promise<LabCatalogEntry | null> {
  const response = await fetch(`${backendOrigin()}/api/v1/labs/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!response.ok) return null;
  return toCatalogLab(await response.json() as ApiLab);
}
