import { NextRequest, NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { prisma } from "@/lib/prisma";
import { RunWorkflowRequest } from "@/lib/schemas/workflows";
import { enqueuePipeline } from "@/lib/ml-queue";

const VALID_WORKFLOW_TYPES = new Set([
  "biomarker_discovery",
  "sample_qc",
  "prompt_optimization",
  "cosmo_pipeline",
]);

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { workflow_type, params } = RunWorkflowRequest.parse(body);

  if (!VALID_WORKFLOW_TYPES.has(workflow_type)) {
    return NextResponse.json(
      {
        error: `Invalid workflow type: ${workflow_type}. Valid: ${[...VALID_WORKFLOW_TYPES].join(", ")}`,
      },
      { status: 400 },
    );
  }

  const workflowId = `${workflow_type}-${uuidv4().slice(0, 12)}`;

  const workflow = await prisma.workflowExecution.create({
    data: {
      id: workflowId,
      workflowType: workflow_type,
      status: "pending",
      params: (params ?? {}) as Record<string, unknown>,
    },
  });

  await enqueuePipeline({ workflowId });

  return NextResponse.json({
    workflow_id: workflow.id,
    status: workflow.status,
    message: "Workflow queued",
  });
}
