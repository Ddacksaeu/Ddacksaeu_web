import type { Metadata } from "next";

import { AppHeader } from "../../src/components/app-header";
import { LabCatalogExplorer } from "../../src/features/catalog/lab-catalog-explorer";
import { LAB_CATALOG_FIXTURES } from "../../src/fixtures/catalog";

export const metadata: Metadata = { title: "Professor search | Ddaksaeu", description: "Explore graduate faculty by university and research keyword." };

type ProfessorsPageProperties = Readonly<{ searchParams: Promise<{ q?: string | string[] }> }>;

export default async function ProfessorsPage({ searchParams }: ProfessorsPageProperties) {
  const parameters = await searchParams;
  const initialQuery = typeof parameters.q === "string" ? parameters.q : "";
  return <div className="site-shell"><AppHeader current="professors" /><LabCatalogExplorer initialQuery={initialQuery} labs={LAB_CATALOG_FIXTURES} mode="search" /></div>;
}
