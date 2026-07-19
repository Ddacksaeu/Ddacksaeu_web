import { describe, expect, it } from "vitest";

import { MAX_DOCUMENT_BYTES, validateDocumentFile } from "./documents-api";

describe("validateDocumentFile", () => {
  it("accepts supported non-empty CV files within the backend limit", () => {
    expect(validateDocumentFile(new File(["CV"], "candidate.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }))).toBeNull();
  });

  it.each([
    ["unsupported extension", new File(["CV"], "candidate.png", { type: "image/png" })],
    ["empty file", new File([], "candidate.txt", { type: "text/plain" })],
    ["oversized file", new File([new Uint8Array(MAX_DOCUMENT_BYTES + 1)], "candidate.txt", { type: "text/plain" })],
  ])("rejects %s", (_name, file) => {
    expect(validateDocumentFile(file)).not.toBeNull();
  });
});
