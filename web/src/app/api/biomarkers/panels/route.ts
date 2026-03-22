import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// Fallback demo panels when DB is empty
const DEMO_PANELS = [
  {
    id: 1,
    target: "msi",
    modality: "proteomics",
    n_features: 26,
    features: [
      { gene: "TAP1", importance: 0.15 },
      { gene: "LCP1", importance: 0.12 },
      { gene: "PTPN6", importance: 0.1 },
      { gene: "ICAM1", importance: 0.09 },
      { gene: "ITGB2", importance: 0.08 },
    ],
    created_at: "2025-01-01T00:00:00Z",
  },
  {
    id: 2,
    target: "msi",
    modality: "rnaseq",
    n_features: 26,
    features: [
      { gene: "EPDR1", importance: 0.14 },
      { gene: "CIITA", importance: 0.11 },
      { gene: "IRF1", importance: 0.1 },
      { gene: "GBP4", importance: 0.09 },
      { gene: "LAG3", importance: 0.08 },
    ],
    created_at: "2025-01-01T00:00:00Z",
  },
];

export async function GET() {
  try {
    const panels = await prisma.biomarkerPanel.findMany({
      orderBy: { createdAt: "desc" },
    });

    if (panels.length > 0) {
      return NextResponse.json(
        panels.map((p) => ({
          id: p.id,
          target: p.target,
          modality: p.modality,
          n_features: Array.isArray(p.features)
            ? (p.features as unknown[]).length
            : 0,
          features: p.features,
          created_at: p.createdAt.toISOString(),
        })),
      );
    }
  } catch {
    // DB not available, use demo data
  }

  return NextResponse.json(DEMO_PANELS);
}
