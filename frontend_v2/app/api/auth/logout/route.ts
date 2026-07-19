import { NextResponse } from "next/server";

import { BACKEND_SESSION_COOKIE } from "../../../../src/server/backend/client";

export async function POST(): Promise<NextResponse> {
  const response = NextResponse.json({ signedOut: true });
  response.cookies.set(BACKEND_SESSION_COOKIE, "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 });
  return response;
}
