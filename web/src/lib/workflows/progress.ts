import { prisma } from "@/lib/prisma";
import type { WorkflowStatus } from "./types";

export async function updateProgress(
  workflowId: string,
  update: {
    status?: WorkflowStatus;
    currentPhase?: string;
    phaseCompleted?: string;
    result?: Record<string, unknown>;
    error?: string;
  },
): Promise<void> {
  const workflow = await prisma.workflowExecution.findUnique({
    where: { id: workflowId },
  });
  if (!workflow) return;

  const data: Record<string, unknown> = {};

  if (update.status) data.status = update.status;
  if (update.currentPhase) data.currentPhase = update.currentPhase;
  if (update.phaseCompleted) {
    const completed = [...workflow.phasesCompleted];
    if (!completed.includes(update.phaseCompleted)) {
      completed.push(update.phaseCompleted);
    }
    data.phasesCompleted = completed;
    data.phasesRemaining = workflow.phasesRemaining.filter(
      (p) => p !== update.phaseCompleted,
    );
  }
  if (update.result) data.result = update.result;
  if (update.error) data.error = update.error;
  if (update.status === "completed" || update.status === "failed") {
    data.completedAt = new Date();
  }

  await prisma.workflowExecution.update({
    where: { id: workflowId },
    data,
  });
}

export async function getProgress(workflowId: string) {
  const workflow = await prisma.workflowExecution.findUnique({
    where: { id: workflowId },
  });
  if (!workflow) return null;

  return {
    workflow_id: workflow.id,
    workflow_type: workflow.workflowType,
    status: workflow.status,
    current_phase: workflow.currentPhase,
    phases_completed: workflow.phasesCompleted,
    phases_remaining: workflow.phasesRemaining,
    started_at: workflow.startedAt.toISOString(),
    completed_at: workflow.completedAt?.toISOString() ?? null,
    error: workflow.error,
  };
}
