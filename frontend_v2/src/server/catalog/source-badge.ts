import type { LabCatalogEntry } from "./schema";

export function createSourceBadge(lab: LabCatalogEntry) {
  return {
    label: "Official institution website",
    href: lab.officialSourceUrl,
    checkedLabel: "Checked",
    verifiedAt: lab.verifiedAt,
  } as const;
}
