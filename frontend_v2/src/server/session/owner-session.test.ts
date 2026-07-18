import { describe, expect, it } from "vitest";

import {
  createOwnerId,
  issueOwnerCookie,
  serializeOwnerCookie,
  verifyOwnerCookie,
} from "./owner-session";

describe("owner session cookie", () => {
  it("round-trips a server-signed anonymous owner", () => {
    // Given
    const ownerId = createOwnerId("anonymous-owner");

    // When
    const cookie = issueOwnerCookie(ownerId, "test-secret-with-enough-length");

    // Then
    expect(verifyOwnerCookie(cookie, "test-secret-with-enough-length")).toEqual(ownerId);
  });

  it("rejects a tampered owner cookie", () => {
    // Given
    const cookie = issueOwnerCookie(createOwnerId("owner"), "test-secret-with-enough-length");

    // When
    const verified = verifyOwnerCookie(`${cookie}x`, "test-secret-with-enough-length");

    // Then
    expect(verified).toBeNull();
  });
});

it("marks production owner cookies Secure", () => {
  expect(serializeOwnerCookie("signed", true)).toContain("; Secure");
});
