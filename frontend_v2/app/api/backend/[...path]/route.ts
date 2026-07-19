import { backendHeaders, backendOrigin } from "../../../../src/server/backend/client";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, { params }: Context): Promise<Response> {
  const { path } = await params;
  const url = new URL(request.url);
  const target = `${backendOrigin()}/api/v1/${path.map(encodeURIComponent).join("/")}${url.search}`;
  const headers = await backendHeaders(request);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  const init: RequestInit = { method: request.method, headers, cache: "no-store" };
  if (request.method !== "GET" && request.method !== "HEAD") init.body = await request.arrayBuffer();
  const upstream = await fetch(target, init);
  if (upstream.status === 204 || upstream.status === 304) {
    return new Response(null, { status: upstream.status });
  }
  return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" } });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
