const SESSION_KEY = "ddacksaeu.auth";

export type AuthSession = { accessToken: string; userId: string; email: string; name: string };

export function getSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(SESSION_KEY);
    return value ? (JSON.parse(value) as AuthSession) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSession) {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession() {
  window.localStorage.removeItem(SESSION_KEY);
}

export function isLoggedIn() {
  return Boolean(getSession()?.accessToken);
}
