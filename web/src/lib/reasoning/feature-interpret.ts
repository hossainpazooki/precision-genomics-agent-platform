/**
 * Feature interpretation reasoning module — replaces dspy_modules/feature_interpret.py.
 * Uses Anthropic TypeScript SDK with structured prompts instead of DSPy.
 */
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const MODEL = "claude-sonnet-4-20250514";

export interface FeatureInterpretResult {
  pathway: string;
  mechanism: string;
  confidence: number;
  pubmedIds: string[];
}

export async function interpretFeature(
  geneName: string,
  expressionContext: string,
  target: string,
): Promise<FeatureInterpretResult> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are a genomics researcher interpreting a gene feature in biological context.

Gene: ${geneName}
Expression Context: ${expressionContext}
Prediction Target: ${target}

Provide:
1. The biological pathway the gene belongs to
2. A proposed mechanism linking the gene to the prediction target
3. Your confidence (0-1)
4. Supporting PubMed IDs

Respond in JSON: {"pathway": "...", "mechanism": "...", "confidence": 0.8, "pubmed_ids": ["12345678"]}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      pathway: parsed.pathway ?? "Unknown",
      mechanism: parsed.mechanism ?? text,
      confidence: parsed.confidence ?? 0.5,
      pubmedIds: parsed.pubmed_ids ?? [],
    };
  } catch {
    return {
      pathway: "Unknown",
      mechanism: text,
      confidence: 0.5,
      pubmedIds: [],
    };
  }
}

/**
 * Interpret a batch of features in parallel.
 */
export async function interpretFeatureBatch(
  features: Array<{ geneName: string; expressionContext: string }>,
  target: string,
): Promise<FeatureInterpretResult[]> {
  return Promise.all(
    features.map((f) =>
      interpretFeature(f.geneName, f.expressionContext, target),
    ),
  );
}
