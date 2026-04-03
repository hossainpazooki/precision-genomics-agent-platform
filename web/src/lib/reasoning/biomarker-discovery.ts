/**
 * Biomarker discovery reasoning module — replaces dspy_modules/biomarker_discovery.py.
 * Uses Anthropic TypeScript SDK with structured prompts instead of DSPy.
 */
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const MODEL = "claude-sonnet-4-20250514";

export interface DataQualityAssessment {
  assessment: string;
  qualityScore: number;
}

export interface ImputationEvaluation {
  evaluation: string;
  recommendation: string;
}

export interface FeatureInterpretation {
  interpretations: string;
  confidence: number;
}

export interface BiomarkerDiscoveryReport {
  report: string;
  recommendations: string;
}

export async function assessDataQuality(
  datasetSummary: string,
): Promise<DataQualityAssessment> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are a bioinformatics expert assessing genomics dataset quality for biomarker discovery.

Dataset Summary:
${datasetSummary}

Provide:
1. A quality assessment narrative
2. A quality score between 0 and 1

Respond in JSON: {"assessment": "...", "quality_score": 0.85}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      assessment: parsed.assessment ?? text,
      qualityScore: parsed.quality_score ?? 0.5,
    };
  } catch {
    return { assessment: text, qualityScore: 0.5 };
  }
}

export async function evaluateImputation(
  imputationStats: string,
): Promise<ImputationEvaluation> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [
      {
        role: "user",
        content: `You are a bioinformatics expert evaluating missing data imputation for genomics.

Imputation Statistics:
${imputationStats}

Provide:
1. An evaluation of imputation quality
2. A recommendation for imputation strategy

Respond in JSON: {"evaluation": "...", "recommendation": "..."}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      evaluation: parsed.evaluation ?? text,
      recommendation: parsed.recommendation ?? "Use NMF imputation",
    };
  } catch {
    return { evaluation: text, recommendation: "Use NMF imputation" };
  }
}

export async function interpretFeatures(
  featureList: string,
  target: string,
): Promise<FeatureInterpretation> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 2048,
    messages: [
      {
        role: "user",
        content: `You are a genomics researcher interpreting selected features in biological context.

Selected Features/Genes:
${featureList}

Prediction Target: ${target}

Provide biological interpretations of these features and their relevance to the prediction target. Include pathway associations and known mechanisms.

Respond in JSON: {"interpretations": "...", "confidence": 0.8}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      interpretations: parsed.interpretations ?? text,
      confidence: parsed.confidence ?? 0.5,
    };
  } catch {
    return { interpretations: text, confidence: 0.5 };
  }
}

export async function synthesizeReport(
  qualityAssessment: string,
  imputationEval: string,
  featureInterpretations: string,
): Promise<BiomarkerDiscoveryReport> {
  const response = await client.messages.create({
    model: MODEL,
    max_tokens: 4096,
    messages: [
      {
        role: "user",
        content: `You are a precision genomics expert synthesizing a biomarker discovery report.

Data Quality Assessment:
${qualityAssessment}

Imputation Evaluation:
${imputationEval}

Feature Interpretations:
${featureInterpretations}

Synthesize a comprehensive biomarker discovery report with actionable recommendations.

Respond in JSON: {"report": "...", "recommendations": "..."}`,
      },
    ],
  });

  const text =
    response.content[0].type === "text" ? response.content[0].text : "";
  try {
    const parsed = JSON.parse(text);
    return {
      report: parsed.report ?? text,
      recommendations: parsed.recommendations ?? "",
    };
  } catch {
    return { report: text, recommendations: "" };
  }
}

/**
 * Run the full biomarker discovery reasoning pipeline.
 * Mirrors BiomarkerDiscoveryModule.forward() from DSPy.
 */
export async function runBiomarkerDiscoveryReasoning(params: {
  datasetSummary: string;
  imputationStats: string;
  featureList: string;
  target: string;
}): Promise<BiomarkerDiscoveryReport> {
  const quality = await assessDataQuality(params.datasetSummary);
  const imputation = await evaluateImputation(params.imputationStats);
  const features = await interpretFeatures(params.featureList, params.target);
  return synthesizeReport(
    quality.assessment,
    imputation.evaluation,
    features.interpretations,
  );
}
