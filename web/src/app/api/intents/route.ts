/**
 * Proxy to Go intent-controller: POST /api/v1/intents, GET /api/v1/intents
 */
import { NextRequest, NextResponse } from "next/server";
import { createIntent, listIntents } from "@/lib/intent-client";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const intent = await createIntent(body);
    return NextResponse.json(intent, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const status = searchParams.get("status") ?? undefined;
    const type = searchParams.get("type") ?? undefined;
    const intents = await listIntents({ status, type });
    return NextResponse.json(intents);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
