import type { BrowserContext, Page } from "@playwright/test";

type SessionTarget = Pick<BrowserContext | Page, "addInitScript" | "request">;

let accountCounter = 0;

async function startBackendSession(target: SessionTarget): Promise<void> {
  accountCounter += 1;
  const response = await target.request.post("/api/auth/signup", {
    data: {
      email: `playwright-${Date.now()}-${accountCounter}@example.test`,
      name: "Playwright Researcher",
      password: "playwright-demo-password",
    },
  });

  if (!response.ok()) {
    throw new Error(`Could not create a Playwright backend session (${response.status()}).`);
  }
}

export async function useSignedInDemo(target: SessionTarget): Promise<void> {
  await startBackendSession(target);
  await target.addInitScript(() => {
    window.localStorage.setItem("ddaksaewoo:demo-session", "signed-in");
    window.localStorage.setItem("ddaksaewoo:demo-onboarding", "complete");
  });
}

export async function useSignedInBeforeOnboarding(target: SessionTarget): Promise<void> {
  await startBackendSession(target);
  await target.addInitScript(() => {
    window.localStorage.setItem("ddaksaewoo:demo-session", "signed-in");
    window.localStorage.removeItem("ddaksaewoo:demo-onboarding");
  });
}
