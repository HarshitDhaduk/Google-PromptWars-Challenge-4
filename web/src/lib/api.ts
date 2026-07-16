/**
 * Typed client for the Next.js BFF routes (which proxy the Python service).
 * All failures are normalized into ApiError so the UI can react by code.
 */

import type {
  ChatApiResponse,
  ContextResponse,
  CrowdResponse,
  Locale,
  SeatsResponse,
  StadiumResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ErrorEnvelope {
  error?: { code?: string; message?: string };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { cache: "no-store", ...init });
  } catch {
    throw new ApiError(0, "network", "Network request failed");
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON body; fall through to the status check.
  }

  if (!response.ok) {
    const envelope = (body ?? {}) as ErrorEnvelope;
    throw new ApiError(
      response.status,
      envelope.error?.code ?? "http_error",
      envelope.error?.message ?? `Request failed with status ${response.status}`,
    );
  }
  return body as T;
}

export function fetchStadium(): Promise<StadiumResponse> {
  return request<StadiumResponse>("/api/stadium");
}

export function fetchCrowd(): Promise<CrowdResponse> {
  return request<CrowdResponse>("/api/crowd");
}

export function fetchContext(): Promise<ContextResponse> {
  return request<ContextResponse>("/api/context");
}

export function fetchSeats(): Promise<SeatsResponse> {
  return request<SeatsResponse>("/api/seats");
}

export interface ChatPayload {
  session_id: string;
  message: string;
  locale: Locale;
}

export function postChat(payload: ChatPayload): Promise<ChatApiResponse> {
  return request<ChatApiResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
