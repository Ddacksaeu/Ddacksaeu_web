const SESSION_KEY = "ddaksaewoo:demo-session";
const ONBOARDING_KEY = "ddaksaewoo:demo-onboarding";
const ACTIVE_SESSION = "signed-in";
const COMPLETED_ONBOARDING = "complete";

export function hasDemoSession(storage: Storage): boolean {
  return storage.getItem(SESSION_KEY) === ACTIVE_SESSION;
}

export function hasCompletedDemoOnboarding(storage: Storage): boolean {
  return storage.getItem(ONBOARDING_KEY) === COMPLETED_ONBOARDING;
}

export function startDemoSession(storage: Storage): void {
  storage.setItem(SESSION_KEY, ACTIVE_SESSION);
}

export function completeDemoOnboarding(storage: Storage): void {
  storage.setItem(ONBOARDING_KEY, COMPLETED_ONBOARDING);
}

export function endDemoSession(storage: Storage): void {
  storage.removeItem(SESSION_KEY);
  storage.removeItem(ONBOARDING_KEY);
}
