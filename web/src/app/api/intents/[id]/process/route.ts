/**
 * Proxy to Go intent-controller: POST /api/v1/intents/:id/process
 */
import { NextRequest, NextResponse } from "next/server";
import { processIntent } from "@/lib/intent-client";

export async function POST(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const intent = await processIntent(id);
    return NextResponse.json(intent);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
