import { z } from "zod";

import { errorJson, proxyPost } from "../../../lib/bff";

// First validation layer; the Python service re-validates with Pydantic.
const chatRequestSchema = z.object({
  session_id: z.uuid(),
  message: z.string().trim().min(1).max(500),
  locale: z.enum(["en", "es", "fr", "ar", "pt", "de"]),
});

export async function POST(request: Request) {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return errorJson(400, "bad_json", "Request body must be JSON.");
  }

  const parsed = chatRequestSchema.safeParse(payload);
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    const where = issue.path.join(".") || "body";
    return errorJson(422, "validation_error", `${where}: ${issue.message}`);
  }

  return proxyPost("/api/chat", parsed.data);
}
