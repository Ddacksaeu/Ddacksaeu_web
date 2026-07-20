import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentApiError, getDocumentHistory, getLatestDocumentAnalysis, MAX_DOCUMENT_BYTES, validateDocumentFile } from "./documents-api";

const originalFetch = global.fetch;

afterEach(() => { global.fetch = originalFetch; });

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

  it("treats a missing latest CV as an empty state instead of a network failure", async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "http_404" } }), { status: 404 }));

    await expect(getLatestDocumentAnalysis()).resolves.toBeNull();
  });

  it.each([
    [401, "http_401", "Your session has expired. Please sign in again."],
    [500, "internal_error", "The server could not process this request."],
    [503, "backend_unavailable", "Could not connect to the server. Check that the backend is running."],
  ])("keeps HTTP %i distinct from a network error", async (status, code, message) => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code } }), { status }));

    await expect(getDocumentHistory()).rejects.toMatchObject({ status, message });
  });

  it("reports a fetch rejection as a network failure", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("network down"));

    await expect(getDocumentHistory()).rejects.toBeInstanceOf(DocumentApiError);
    await expect(getDocumentHistory()).rejects.toMatchObject({ status: 0, message: "Could not connect to the server. Check that the backend is running." });
  });
});
