/**
 * Proxy to Go intent-controller: GET/DELETE /api/v1/intents/:id
 */
import { NextRequest, NextResponse } from "next/server";
import { getIntent, cancelIntent } from "@/lib/intent-client";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const intent = await getIntent(id);
    return NextResponse.json(intent);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    const status = message.includes("not found") ? 404 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const intent = await cancelIntent(id);
    return NextResponse.json(intent);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
