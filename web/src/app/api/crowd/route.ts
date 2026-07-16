import { proxyGet } from "../../../lib/bff";

export async function GET() {
  return proxyGet("/api/crowd");
}
