/**
 * Regulatory report reasoning module — replaces dspy_modules/regulatory_report.py.
 * Uses Anthropic TypeScript SDK with structured prompts instead of DSPy.
 */
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const MODEL = "claude-sonnet-4-20250514";

export interface RegulatoryReport {
  report: string;
  riskAssessment: string;
  recommendations: string;
}

export async function generateRegulatoryReport(
  analysisResults: string,
  biomarkerPanel: string,
  qcSummary: string,
): Promise<RegulatoryReport> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 4096,
    messages: [
      {
        role: "user",
        content: `You are a regulatory affairs specialist generating a compliance report for a biomarker discovery analysis.

Analysis Results:
${analysisResults}

Biomarker Panel:
${biomarkerPanel}

Quality Control Summary:
${qcSummary}

Generate a regulatory-compliant report covering:
1. Full report text suitable for regulatory submission
2. Risk assessment for the biomarker panel
3. Regulatory recommendations

Respond in JSON: {"report": "...", "risk_assessment": "...", "recommendations": "..."}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      report: parsed.report ?? text,
      riskAssessment: parsed.risk_assessment ?? "",
      recommendations: parsed.recommendations ?? "",
    };
  } catch {
    return { report: text, riskAssessment: "", recommendations: "" };
  }
}
