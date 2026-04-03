/**
 * Sample QC reasoning module — replaces dspy_modules/sample_qc.py.
 * Uses Anthropic TypeScript SDK with structured prompts instead of DSPy.
 */
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const MODEL = "claude-sonnet-4-20250514";

export interface ClassificationAnalysis {
  analysis: string;
  flaggedSamples: string[];
  confidence: number;
}

export interface DistanceAnalysis {
  analysis: string;
  flaggedSamples: string[];
  confidence: number;
}

export interface CrossValidationResult {
  concordantFlags: string[];
  summary: string;
  concordanceRate: number;
}

export async function analyzeClassification(
  classificationResults: string,
  target: string,
): Promise<ClassificationAnalysis> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are a bioinformatics QC expert analyzing classification-based quality control results.

Classification Results:
${classificationResults}

Prediction Target: ${target}

Analyze the classification QC results and identify flagged samples.

Respond in JSON: {"analysis": "...", "flagged_samples": ["S001", "S002"], "confidence": 0.85}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      analysis: parsed.analysis ?? text,
      flaggedSamples: parsed.flagged_samples ?? [],
      confidence: parsed.confidence ?? 0.5,
    };
  } catch {
    return { analysis: text, flaggedSamples: [], confidence: 0.5 };
  }
}

export async function analyzeDistance(
  distanceResults: string,
): Promise<DistanceAnalysis> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are a bioinformatics QC expert analyzing distance matrix-based quality control results.

Distance Matrix Results:
${distanceResults}

Analyze the distance-based QC results and identify flagged samples.

Respond in JSON: {"analysis": "...", "flagged_samples": ["S001", "S002"], "confidence": 0.85}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      analysis: parsed.analysis ?? text,
      flaggedSamples: parsed.flagged_samples ?? [],
      confidence: parsed.confidence ?? 0.5,
    };
  } catch {
    return { analysis: text, flaggedSamples: [], confidence: 0.5 };
  }
}

export async function crossValidateFlags(
  classificationFlags: string[],
  distanceFlags: string[],
): Promise<CrossValidationResult> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are a bioinformatics QC expert cross-validating flags from multiple QC methods.

Classification Flags: ${classificationFlags.join(", ") || "none"}
Distance Flags: ${distanceFlags.join(", ") || "none"}

Cross-validate the flags and determine concordant flags (agreed upon by both methods).

Respond in JSON: {"concordant_flags": ["S001"], "summary": "...", "concordance_rate": 0.75}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      concordantFlags: parsed.concordant_flags ?? [],
      summary: parsed.summary ?? text,
      concordanceRate: parsed.concordance_rate ?? 0.0,
    };
  } catch {
    // Compute concordance programmatically as fallback
    const classSet = new Set(classificationFlags);
    const concordant = distanceFlags.filter((f) => classSet.has(f));
    const total = new Set([...classificationFlags, ...distanceFlags]).size;
    return {
      concordantFlags: concordant,
      summary: text,
      concordanceRate: total > 0 ? concordant.length / total : 0,
    };
  }
}

/**
 * Run the full sample QC reasoning pipeline.
 * Mirrors SampleQCModule.forward() from DSPy.
 */
export async function runSampleQCReasoning(params: {
  classificationResults: string;
  distanceResults: string;
  target: string;
}): Promise<CrossValidationResult> {
  const classification = await analyzeClassification(
    params.classificationResults,
    params.target,
  );
  const distance = await analyzeDistance(params.distanceResults);
  return crossValidateFlags(
    classification.flaggedSamples,
    distance.flaggedSamples,
  );
}
