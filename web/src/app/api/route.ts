import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    name: "Precision Genomics Agent Platform",
    version: "0.1.0",
    docs: "/api",
  });
}
