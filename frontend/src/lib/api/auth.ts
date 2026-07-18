import type { AuthSession } from "../auth";
import { apiFetch } from "./client";

type AuthPayload = { access_token: string; user_id: string; email: string; name: string };

async function submit(path: string, body: Record<string, string>): Promise<AuthSession> {
  const response = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "인증에 실패했습니다.");
  const payload = (await response.json()) as AuthPayload;
  return { accessToken: payload.access_token, userId: payload.user_id, email: payload.email, name: payload.name };
}

export const signup = (email: string, password: string, name: string) => submit("/auth/signup", { email, password, name });
export const login = (email: string, password: string) => submit("/auth/login", { email, password });
