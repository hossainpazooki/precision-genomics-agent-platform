import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const panelId = parseInt(id, 10);

  if (isNaN(panelId)) {
    return NextResponse.json({ error: "Invalid panel ID" }, { status: 400 });
  }

  try {
    const panel = await prisma.biomarkerPanel.findUnique({
      where: { id: panelId },
    });

    if (panel) {
      return NextResponse.json({
        panel_id: panel.id,
        target: panel.target,
        modality: panel.modality,
        features: panel.features,
        n_features: Array.isArray(panel.features)
          ? (panel.features as unknown[]).length
          : 0,
      });
    }
  } catch {
    // DB not available
  }

  return NextResponse.json(
    { error: `Panel ${panelId} not found` },
    { status: 404 },
  );
}
