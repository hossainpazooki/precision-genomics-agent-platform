import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  const workflow = await prisma.workflowExecution.findUnique({
    where: { id },
  });

  if (!workflow) {
    return NextResponse.json(
      { error: `Workflow ${id} not found` },
      { status: 404 },
    );
  }

  return NextResponse.json({
    workflow_id: workflow.id,
    workflow_type: workflow.workflowType,
    status: workflow.status,
    current_phase: workflow.currentPhase,
    phases_completed: workflow.phasesCompleted,
    phases_remaining: workflow.phasesRemaining,
    started_at: workflow.startedAt.toISOString(),
    completed_at: workflow.completedAt?.toISOString() ?? null,
  });
}
