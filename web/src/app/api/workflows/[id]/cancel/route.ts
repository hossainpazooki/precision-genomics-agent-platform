/**
 * Cancel workflow — proxy to Go intent-controller.
 */
import { NextRequest, NextResponse } from "next/server";
import { cancelWorkflow } from "@/lib/intent-client";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const result = await cancelWorkflow(id);
    return NextResponse.json({
      workflow_id: id,
      ...result,
      message: "Workflow cancelled",
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
