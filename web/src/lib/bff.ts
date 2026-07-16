/**
 * Server-side helpers for the BFF route handlers.
 *
 * The browser never talks to the Python service directly: these helpers run
 * on the Next.js server, so the service URL (and everything behind it) stays
 * private to the backend.
 */

import { NextResponse } from "next/server";

export const SERVICE_URL = process.env.SERVICE_URL ?? "http://127.0.0.1:8000";

export function errorJson(status: number, code: string, message: string): NextResponse {
  return NextResponse.json({ error: { code, message } }, { status });
}

export function serviceUnavailable(): NextResponse {
  return errorJson(
    503,
    "service_unavailable",
    "The assistant service is not reachable. Start it with: cd service && python run.py",
  );
}

/** Forward an upstream service response, preserving status and JSON body. */
async function forward(upstream: Response): Promise<NextResponse> {
  let body: unknown;
  try {
    body = await upstream.json();
  } catch {
    return serviceUnavailable();
  }
  return NextResponse.json(body, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}

export async function proxyGet(path: string, timeoutMs = 5_000): Promise<NextResponse> {
  try {
    const upstream = await fetch(`${SERVICE_URL}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    return await forward(upstream);
  } catch {
    return serviceUnavailable();
  }
}

export async function proxyPost(
  path: string,
  payload: unknown,
  timeoutMs = 30_000,
): Promise<NextResponse> {
  try {
    const upstream = await fetch(`${SERVICE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    return await forward(upstream);
  } catch {
    return serviceUnavailable();
  }
}
