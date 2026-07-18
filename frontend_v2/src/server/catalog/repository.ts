import { LabCatalogSchema, type LabCatalogEntry } from "./schema";

type CatalogSearch = {
  readonly institution?: string;
  readonly topic?: string;
};

export function createCatalogRepository(input: unknown) {
  const catalog = LabCatalogSchema.parse(input);
  return {
    list: (): readonly LabCatalogEntry[] => catalog,
    search: (filter: CatalogSearch): readonly LabCatalogEntry[] =>
      catalog.filter((lab) =>
        (filter.institution === undefined || lab.institution === filter.institution) &&
        (filter.topic === undefined || lab.topics.includes(filter.topic)),
      ),
  } as const;
}
