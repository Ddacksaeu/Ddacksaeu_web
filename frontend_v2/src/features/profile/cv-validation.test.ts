import { describe, expect, it } from "vitest";

import { InvalidCvError, validateCvUpload } from "./cv-validation";

describe("validateCvUpload", () => {
  it("accepts PDF and text CVs within five megabytes", () => {
    // Given
    const input = {
      bytes: new Uint8Array([37, 80, 68, 70, 45]),
      contentType: "application/pdf",
      fileName: "cv.pdf",
    };

    // When
    const result = validateCvUpload(input);

    // Then
    expect(result.contentType).toBe("application/pdf");
  });

  it.each([
    ["unsupported type", "image/png", 1],
    ["oversized file", "text/plain", 5 * 1024 * 1024 + 1],
  ])("rejects an %s", (_label, contentType, size) => {
    // Given
    const input = { bytes: new Uint8Array(size), contentType, fileName: "cv" };

    // When
    const validating = () => validateCvUpload(input);

    // Then
    expect(validating).toThrow(InvalidCvError);
  });

  it("rejects PDF MIME without a PDF signature", () => {
    const input = {
      bytes: new Uint8Array([1, 2, 3]),
      contentType: "application/pdf",
      fileName: "cv.pdf",
    };
    expect(() => validateCvUpload(input)).toThrow(InvalidCvError);
  });

  it("rejects an empty text CV", () => {
    const input = {
      bytes: new Uint8Array(),
      contentType: "text/plain",
      fileName: "cv.txt",
    };
    expect(() => validateCvUpload(input)).toThrow(InvalidCvError);
  });
});
