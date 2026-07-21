import { NextResponse } from "next/server";

import { BACKEND_SESSION_COOKIE, backendOrigin } from "../../../../src/server/backend/client";
import { isShowcaseMode, SHOWCASE_UNAVAILABLE_MESSAGE } from "../../../../src/features/showcase/mode";

export async function POST(request: Request): Promise<NextResponse> {
  if (isShowcaseMode()) return NextResponse.json({ detail: SHOWCASE_UNAVAILABLE_MESSAGE }, { status: 503 });
  const payload = await request.json();
  const upstream = await fetch(`${backendOrigin()}/api/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload), cache: "no-store",
  });
  const body = await upstream.json();
  if (!upstream.ok) return NextResponse.json(body, { status: upstream.status });
  const response = NextResponse.json({ user: { userId: body.user_id, email: body.email, name: body.name } });
  response.cookies.set(BACKEND_SESSION_COOKIE, body.access_token, { httpOnly: true, sameSite: "lax", secure: process.env["NODE_ENV"] === "production", path: "/", maxAge: 60 * 60 * 24 * 7 });
  return response;
}
