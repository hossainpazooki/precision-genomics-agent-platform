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

  if (workflow.status !== "completed") {
    return NextResponse.json({
      workflow_id: id,
      status: workflow.status,
      message: "Workflow has not completed yet",
    });
  }

  return NextResponse.json({
    workflow_id: id,
    report: workflow.result,
  });
}
