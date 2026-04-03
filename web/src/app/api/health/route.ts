import { NextResponse } from "next/server";
import { mlHealth } from "@/lib/ml-client";

export async function GET() {
  let mlStatus = "unknown";
  try {
    const ml = await mlHealth();
    mlStatus = ml.status;
  } catch {
    mlStatus = "unavailable";
  }

  return NextResponse.json({
    status: "healthy",
    version: "0.1.0",
    services: {
      web: "healthy",
      ml: mlStatus,
    },
  });
}
