/**
 * Claude activities — direct Anthropic TS SDK calls.
 * Replaces workflows/activities/claude_activities.py.
 */

import Anthropic from "@anthropic-ai/sdk";
import type { WorkflowContext } from "../types";

function getClient(): Anthropic {
  return new Anthropic();
}

export async function generateInterpretation(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const featurePhase = ctx.results.get("feature_selection");
  const panels = (featurePhase?.feature_panels as Array<Record<string, unknown>>) ?? [];
  const features = panels.flatMap(
    (p) =>
      ((p.biomarkers as Array<Record<string, unknown>>) ?? []).map(
        (b) => b.gene as string,
      ),
  );
  const target = (ctx.params.target as string) ?? "msi";

  if (features.length === 0) {
    return {
      interpretation: {
        summary: "No features selected for interpretation.",
        features: [],
      },
    };
  }

  const client = getClient();
  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2048,
    messages: [
      {
        role: "user",
        content: `You are a genomics expert. Explain the biological relevance of these biomarker genes for ${target} classification in colorectal cancer:

Genes: ${features.join(", ")}

For each gene, provide:
1. Known function in cancer biology
2. Relevance to ${target} (microsatellite instability) if known
3. Pathway associations
4. Clinical significance

Format as JSON array with keys: gene, function, msi_relevance, pathways, clinical_significance.`,
      },
    ],
  });

  const text =
    message.content[0].type === "text" ? message.content[0].text : "";

  return {
    interpretation: {
      summary: `Interpreted ${features.length} biomarker features for ${target}`,
      raw_response: text,
      features,
      target,
    },
  };
}

export async function compileReport(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const allResults = Object.fromEntries(ctx.results);

  const client = getClient();
  const message = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 2048,
    messages: [
      {
        role: "user",
        content: `Summarize this genomics analysis workflow result into a concise report:

${JSON.stringify(allResults, null, 2)}

Include:
1. Executive summary (2-3 sentences)
2. Key findings
3. Recommended next steps
4. Confidence assessment`,
      },
    ],
  });

  const text =
    message.content[0].type === "text" ? message.content[0].text : "";

  return { report: text };
}
