import type { Metadata } from "next";

import { AppHeader } from "../../src/components/app-header";
import { LabCatalogExplorer } from "../../src/features/catalog/lab-catalog-explorer";
import { fetchBackendLabs, type LabSearchResponse } from "../../src/server/backend/labs";

export const metadata: Metadata = { title: "Professor search | Ddaksaeu", description: "Explore graduate faculty by university and research keyword." };

type ProfessorsPageProperties = Readonly<{ searchParams: Promise<{ q?: string | string[] }> }>;

export default async function ProfessorsPage({ searchParams }: ProfessorsPageProperties) {
  const parameters = await searchParams;
  const initialQuery = typeof parameters.q === "string" ? parameters.q : "";
  let labs: Pick<LabSearchResponse, "items" | "total"> = { items: [], total: 0 };
  let initialError = false;
  try { labs = await fetchBackendLabs(initialQuery); } catch { initialError = true; }
  return <div className="site-shell"><AppHeader current="professors" /><LabCatalogExplorer initialQuery={initialQuery} initialLabs={labs.items} initialTotal={labs.total} initialError={initialError} /></div>;
}
