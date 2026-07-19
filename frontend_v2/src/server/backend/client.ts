import { cookies } from "next/headers";

export const BACKEND_SESSION_COOKIE = "ddacksaeu_session";

export function backendOrigin(): string {
  return (process.env["BACKEND_API_ORIGIN"] ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export async function backendHeaders(request: Request): Promise<Headers> {
  const headers = new Headers({ Accept: "application/json" });
  const token = request.headers.get("cookie")
    ?.split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${BACKEND_SESSION_COOKIE}=`))
    ?.slice(BACKEND_SESSION_COOKIE.length + 1)
    ?? (await cookies()).get(BACKEND_SESSION_COOKIE)?.value;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}
