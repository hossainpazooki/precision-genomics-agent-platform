/**
 * Workflow routes — proxy to Go intent-controller for execution,
 * fall back to Prisma for direct DB queries.
 */
import { NextRequest, NextResponse } from "next/server";
import { triggerWorkflow, listWorkflows } from "@/lib/intent-client";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const result = await triggerWorkflow({
      workflow_type: body.workflow_type,
      params: body.params,
    });
    return NextResponse.json(result, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status") ?? undefined;
    const workflows = await listWorkflows({ status });
    return NextResponse.json(workflows);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
