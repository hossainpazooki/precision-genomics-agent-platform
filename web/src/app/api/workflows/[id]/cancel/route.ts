import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(
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

  if (workflow.status === "completed" || workflow.status === "cancelled") {
    return NextResponse.json({
      workflow_id: id,
      status: workflow.status,
      message: `Workflow already ${workflow.status}`,
    });
  }

  const updated = await prisma.workflowExecution.update({
    where: { id },
    data: { status: "cancelled" },
  });

  return NextResponse.json({
    workflow_id: updated.id,
    status: updated.status,
    message: "Workflow cancelled",
  });
}
