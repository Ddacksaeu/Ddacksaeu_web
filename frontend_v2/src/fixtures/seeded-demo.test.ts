import { describe, expect, it } from "vitest";

import { seededDemo } from "./seeded-demo";

describe("seededDemo", () => {
  it("Given the demo fixture, when it is loaded, then it does not claim a profile exists", () => {
    // Given
    const fixture = seededDemo;

    // When
    const status = fixture.profileStatus;

    // Then
    expect(status).toBe("not-created");
  });
});
