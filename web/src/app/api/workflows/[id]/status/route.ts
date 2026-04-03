/**
 * Workflow status — proxy to Go intent-controller.
 */
import { NextRequest, NextResponse } from "next/server";
import { getWorkflow } from "@/lib/intent-client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const workflow = await getWorkflow(id);
    return NextResponse.json({
      workflow_id: workflow.workflow_id,
      workflow_type: workflow.workflow_type,
      status: workflow.status,
      current_phase: workflow.current_phase,
      phases_completed: workflow.phases_completed,
      started_at: workflow.started_at,
      completed_at: workflow.completed_at,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    const status = message.includes("not found") ? 404 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
