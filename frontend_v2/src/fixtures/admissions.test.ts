import { describe, expect, it } from "vitest";

import { ADMISSION_SCHEDULES } from "./admissions";

describe("ADMISSION_SCHEDULES", () => {
  it("keeps every fixture visibly fictional and source-linked", () => {
    const institutions = new Set(ADMISSION_SCHEDULES.map((schedule) => schedule.institution));

    expect(ADMISSION_SCHEDULES).toHaveLength(6);
    expect(institutions.size).toBeGreaterThanOrEqual(4);
    expect(ADMISSION_SCHEDULES.every((schedule) => schedule.dataStatus === "demo")).toBe(true);
    expect(ADMISSION_SCHEDULES.every((schedule) => schedule.scheduleNote === "Fictional schedule for the hackathon demo")).toBe(true);
    expect(ADMISSION_SCHEDULES.every((schedule) => schedule.officialSourceUrl.startsWith("https://"))).toBe(true);
  });
});
