import { rm } from "node:fs/promises";
import { resolve } from "node:path";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

type ProfileRoute = typeof import("../../../app/api/profile/route");

const originalOwnerSessionSecret = process.env["OWNER_SESSION_SECRET"];
const originalProfileDataFile = process.env["PROFILE_DATA_FILE"];
const routeDataFile = resolve(".data", `profile-route-test-${process.pid}.json`);
let GET: ProfileRoute["GET"];
let POST: ProfileRoute["POST"];
let PUT: ProfileRoute["PUT"];
let PATCH: ProfileRoute["PATCH"];

beforeAll(async () => {
  process.env["OWNER_SESSION_SECRET"] = "test-owner-secret-at-least-16";
  process.env["PROFILE_DATA_FILE"] = routeDataFile;
  ({ GET, POST, PUT, PATCH } = await import("../../../app/api/profile/route"));
});

afterAll(async () => {
  await rm(routeDataFile, { force: true });
  if (originalOwnerSessionSecret === undefined) {
    delete process.env["OWNER_SESSION_SECRET"];
  } else {
    process.env["OWNER_SESSION_SECRET"] = originalOwnerSessionSecret;
  }
  if (originalProfileDataFile === undefined) {
    delete process.env["PROFILE_DATA_FILE"];
  } else {
    process.env["PROFILE_DATA_FILE"] = originalProfileDataFile;
  }
});

function cookieFrom(response: Response): string {
  const value = response.headers.get("set-cookie");
  if (value === null) {
    throw new TypeError("Expected owner cookie");
  }
  return value.split(";")[0] ?? value;
}

describe("profile API route", () => {
  it("rejects an unsupported CV after consent", async () => {
    // Given
    const consent = await PUT(
      new Request("http://local/api/profile", {
        method: "PUT",
        body: JSON.stringify({
          consentToStorage: true,
          displayName: "Alex Kim",
          researchInterests: ["vision"],
        }),
      }),
    );
    const form = new FormData();
    form.set(
      "cv",
      new File([new Uint8Array([1])], "cv.png", { type: "image/png" }),
    );
    // When
    const response = await POST(
      new Request("http://local/api/profile", {
        method: "POST",
        headers: { cookie: cookieFrom(consent) },
        body: form,
      }),
    );
    // Then
    expect(response.status).toBe(400);
  });

  it("keeps a second owner profile empty", async () => {
    // Given
    const firstOwner = await PUT(
      new Request("http://local/api/profile", {
        method: "PUT",
        body: JSON.stringify({
          consentToStorage: true,
          displayName: "Owner A",
          researchInterests: [],
        }),
      }),
    );
    expect(firstOwner.status).toBe(200);
    // When
    const secondOwner = await GET(
      new Request("http://local/api/profile", { method: "GET" }),
    );
    // Then
    await expect(secondOwner.json()).resolves.toMatchObject({ profile: null });
  });

  it("serves the local profile workspace when the session secret is missing", async () => {
    // Given
    const previous = process.env["OWNER_SESSION_SECRET"];
    delete process.env["OWNER_SESSION_SECRET"];
    try {
      // When
      const response = await GET(
        new Request("http://local/api/profile", { method: "GET" }),
      );
      // Then
      expect(response.status).toBe(200);
    } finally {
      if (previous === undefined) {
        delete process.env["OWNER_SESSION_SECRET"];
      } else {
        process.env["OWNER_SESSION_SECRET"] = previous;
      }
    }
  });

  it("rejects oversized profile requests before parsing", async () => {
    const response = await PUT(new Request("http://local/api/profile", {
      method: "PUT",
      headers: { "content-length": "70000" },
      body: "{}",
    }));

    expect(response.status).toBe(413);
  });

  it("persists and removes a saved professor for the same owner", async () => {
    const consent = await PUT(new Request("http://local/api/profile", {
      method: "PUT",
      body: JSON.stringify({
        consentToStorage: true,
        displayName: "Alex Kim",
        researchInterests: ["AI"],
      }),
    }));
    const cookie = cookieFrom(consent);

    const saved = await PATCH(new Request("http://local/api/profile", {
      method: "PATCH",
      headers: { cookie },
      body: JSON.stringify({ labId: "snu-demo-01", saved: true }),
    }));
    expect(saved.status).toBe(200);
    const workspace = await GET(new Request("http://local/api/profile", { headers: { cookie } }));
    await expect(workspace.json()).resolves.toMatchObject({ targetLabIds: ["snu-demo-01"] });

    const removed = await PATCH(new Request("http://local/api/profile", {
      method: "PATCH",
      headers: { cookie },
      body: JSON.stringify({ labId: "snu-demo-01", saved: false }),
    }));
    expect(removed.status).toBe(200);
    const cleared = await GET(new Request("http://local/api/profile", { headers: { cookie } }));
    await expect(cleared.json()).resolves.toMatchObject({ targetLabIds: [] });
  });
});
