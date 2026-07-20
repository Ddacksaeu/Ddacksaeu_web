import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "../../../app/api/backend/[...path]/route";

const originalFetch = global.fetch;
const originalOrigin = process.env["BACKEND_API_ORIGIN"];

afterEach(() => {
  global.fetch = originalFetch;
  if (originalOrigin === undefined) delete process.env["BACKEND_API_ORIGIN"];
  else process.env["BACKEND_API_ORIGIN"] = originalOrigin;
});

describe("backend documents BFF", () => {
  it("forwards multipart data, session authentication, and upstream errors", async () => {
    process.env["BACKEND_API_ORIGIN"] = "http://backend.test";
    const upstream = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "empty_file" } }), {
      status: 422,
      headers: { "content-type": "application/json" },
    }));
    global.fetch = upstream;
    const form = new FormData();
    form.set("file", new File(["CV"], "cv.txt", { type: "text/plain" }));

    const response = await POST(new Request("http://local/api/backend/documents/analyze", {
      method: "POST",
      headers: { cookie: "ddacksaeu_session=token-value" },
      body: form,
    }), { params: Promise.resolve({ path: ["documents", "analyze"] }) });

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ error: { code: "empty_file" } });
    const [url, init] = upstream.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://backend.test/api/v1/documents/analyze");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer token-value");
    expect(new Headers(init.headers).get("content-type")).toContain("multipart/form-data; boundary=");
    expect(init.body).toBeInstanceOf(ArrayBuffer);
  });

  it("returns a safe service-unavailable response when FastAPI cannot be reached", async () => {
    process.env["BACKEND_API_ORIGIN"] = "http://backend.test";
    global.fetch = vi.fn().mockRejectedValue(new TypeError("connection refused"));

    const response = await GET(new Request("http://local/api/backend/documents/latest", {
      headers: { cookie: "ddacksaeu_session=token-value" },
    }), {
      params: Promise.resolve({ path: ["documents", "latest"] }),
    });

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({ error: { code: "backend_unavailable", message: "Backend service is unavailable" } });
  });
});
