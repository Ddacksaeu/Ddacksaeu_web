import type { BrowserContext, Page } from "@playwright/test";

type ScriptTarget = Pick<BrowserContext | Page, "addInitScript">;

export async function useSignedInDemo(target: ScriptTarget): Promise<void> {
  await target.addInitScript(() => {
    window.localStorage.setItem("ddaksaewoo:demo-session", "signed-in");
    window.localStorage.setItem("ddaksaewoo:demo-onboarding", "complete");
  });
}

export async function useSignedInBeforeOnboarding(target: ScriptTarget): Promise<void> {
  await target.addInitScript(() => {
    window.localStorage.setItem("ddaksaewoo:demo-session", "signed-in");
    window.localStorage.removeItem("ddaksaewoo:demo-onboarding");
  });
}
