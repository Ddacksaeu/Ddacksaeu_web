import { describe, expect, it } from "vitest"

import { LAB_CATALOG_FIXTURES } from "../../fixtures/catalog"
import { createCatalogRepository } from "./repository"
import { LabCatalogEntrySchema } from "./schema"
import { createSourceBadge } from "./source-badge"

describe("LabCatalogEntrySchema", () => {
  it("rejects a record when officialSourceUrl is missing", () => {
    // Given
    const { officialSourceUrl: _officialSourceUrl, ...record } = LAB_CATALOG_FIXTURES[0]
    // When
    const result = LabCatalogEntrySchema.safeParse(record)
    // Then
    expect(result.success).toBe(false)
  })

  it("rejects a record when verifiedAt is missing", () => {
    // Given
    const { verifiedAt: _verifiedAt, ...record } = LAB_CATALOG_FIXTURES[0]
    // When
    const result = LabCatalogEntrySchema.safeParse(record)
    // Then
    expect(result.success).toBe(false)
  })

  it("rejects non-HTTPS and non-official source links", () => {
    const lab = LAB_CATALOG_FIXTURES[0]
    expect(LabCatalogEntrySchema.safeParse({ ...lab, officialSourceUrl: "ftp://www.snu.ac.kr/" }).success).toBe(false)
    expect(LabCatalogEntrySchema.safeParse({ ...lab, officialSourceUrl: "https://example.com/" }).success).toBe(false)
  })
})

describe("catalog repository", () => {
  it("returns at least twenty demo labs across four Korean institutions", () => {
    // Given
    const repository = createCatalogRepository(LAB_CATALOG_FIXTURES)
    // When
    const labs = repository.list()
    // Then
    expect(labs).toHaveLength(20)
    expect(new Set(labs.map((lab) => lab.institution)).size).toBeGreaterThanOrEqual(4)
    expect(labs.every((lab) => lab.dataStatus === "demo")).toBe(true)
  })

  it("filters labs by institution and topic deterministically", () => {
    // Given
    const repository = createCatalogRepository(LAB_CATALOG_FIXTURES)
    // When
    const labs = repository.search({ institution: "Seoul National University", topic: "AI" })
    // Then
    expect(labs.map((lab) => lab.id)).toEqual(["snu-demo-01", "snu-demo-02"])
  })
})

describe("source badge contract", () => {
  it("links the official source and exposes its verification date", () => {
    // Given
    const lab = LabCatalogEntrySchema.parse(LAB_CATALOG_FIXTURES[0])
    // When
    const badge = createSourceBadge(lab)
    // Then
    expect(badge).toEqual({
      label: "Official institution website",
      href: lab.officialSourceUrl,
      checkedLabel: "Checked",
      verifiedAt: lab.verifiedAt,
    })
  })
})
