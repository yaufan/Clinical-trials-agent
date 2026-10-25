/**
 * Same-origin proxy: browser → /backend/api/... → Next.js server → backend container.
 *
 * Why: the backend and its API key never have to be exposed to the LAN or shipped to the browser.
 * The key is read from BACKEND_API_KEY at request time on the server only. Responses are streamed,
 * so Server-Sent Events (/api/runs/{id}/events) and file downloads pass through unchanged.
 */
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = (process.env.BACKEND_INTERNAL_URL || "http://localhost:8000").replace(/\/$/, "");
const SAFE_SEGMENT = /^[A-Za-z0-9._~\-]+$/;
const FORWARD_REQUEST_HEADERS = ["content-type", "accept", "last-event-id"];
const FORWARD_RESPONSE_HEADERS = ["content-type", "content-disposition", "cache-control", "www-authenticate"];
const MAX_BODY_BYTES = 2 * 1024 * 1024;

type Ctx = { params: Promise<{ path: string[] }> };

async function proxy(req: NextRequest, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params;
  // Only the backend's /api tree is reachable, and only with plain path segments (no "..", no encoded slashes).
  if (!path?.length || path[0] !== "api" || !path.every((p) => SAFE_SEGMENT.test(p) && p !== "." && p !== "..")) {
    return Response.json({ detail: "not found" }, { status: 404 });
  }
  const target = `${BACKEND}/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  for (const h of FORWARD_REQUEST_HEADERS) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  const key = process.env.BACKEND_API_KEY;
  if (key) headers.set("x-api-key", key);

  let body: ArrayBuffer | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.arrayBuffer();
    if (body.byteLength > MAX_BODY_BYTES) {
      return Response.json({ detail: "request body too large" }, { status: 413 });
    }
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, { method: req.method, headers, body, signal: req.signal, redirect: "manual", cache: "no-store" });
  } catch {
    return Response.json({ detail: "backend unreachable" }, { status: 502 });
  }

  const out = new Headers();
  for (const h of FORWARD_RESPONSE_HEADERS) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  if ((upstream.headers.get("content-type") || "").includes("text/event-stream")) {
    out.set("cache-control", "no-cache, no-transform");
    out.set("x-accel-buffering", "no");
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
