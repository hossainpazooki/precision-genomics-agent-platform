/**
 * Proxy to Go intent-controller: GET /api/v1/intents/:id/status
 */
import { NextRequest, NextResponse } from "next/server";
import { getIntentStatus } from "@/lib/intent-client";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const status = await getIntentStatus(id);
    return NextResponse.json(status);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    const status = message.includes("not found") ? 404 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
