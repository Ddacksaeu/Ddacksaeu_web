import { describe, expect, it } from "vitest";

import { ADMISSION_SCHEDULES } from "./admissions";

describe("ADMISSION_SCHEDULES", () => {
  it("keeps every seeded schedule source-linked and marked for verification", () => {
    const institutions = new Set(ADMISSION_SCHEDULES.map((schedule) => schedule.institution));

    expect(ADMISSION_SCHEDULES).toHaveLength(6);
    expect(institutions.size).toBeGreaterThanOrEqual(4);
    expect(ADMISSION_SCHEDULES.every((schedule) => schedule.dataStatus === "demo")).toBe(true);
    expect(ADMISSION_SCHEDULES.every((schedule) => schedule.scheduleNote === "Verify this date on the official admissions website before applying.")).toBe(true);
    expect(ADMISSION_SCHEDULES.every((schedule) => schedule.officialSourceUrl.startsWith("https://"))).toBe(true);
  });
});
