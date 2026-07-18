import type { LabCatalogEntry } from "../../server/catalog/schema";

export type CatalogFilters = Readonly<{
  institution: string;
  topic: string;
  query: string;
}>;

export function filterCatalog(
  labs: readonly LabCatalogEntry[],
  filters: CatalogFilters,
): readonly LabCatalogEntry[] {
  const query = filters.query.trim().toLocaleLowerCase("en-US");

  return labs.filter((lab) => {
    const matchesInstitution =
      filters.institution.length === 0 || lab.institution === filters.institution;
    const matchesTopic = filters.topic.length === 0 || lab.topics.includes(filters.topic);
    const searchableText = [lab.labName, lab.professor, lab.institution, ...lab.topics]
      .join(" ")
      .toLocaleLowerCase("en-US");

    return matchesInstitution && matchesTopic && (query.length === 0 || searchableText.includes(query));
  });
}
