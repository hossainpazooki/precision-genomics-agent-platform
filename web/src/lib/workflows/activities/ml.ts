/**
 * ML activities — proxy to Python ML service via HTTP.
 * Replaces workflows/activities/ml_activities.py.
 */

import * as mlClient from "@/lib/ml-client";
import type { WorkflowContext } from "../types";

export async function imputeData(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const modalities = (ctx.params.modalities as string[]) ?? [
    "proteomics",
    "rnaseq",
  ];
  const results: Record<string, unknown> = {};

  for (const modality of modalities) {
    results[modality] = await mlClient.impute({
      dataset: (ctx.params.dataset as string) ?? "train",
      modality,
    });
  }

  return { imputation_results: results };
}

export async function selectFeatures(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const modalities = (ctx.params.modalities as string[]) ?? [
    "proteomics",
    "rnaseq",
  ];
  const panels: Record<string, unknown>[] = [];

  for (const modality of modalities) {
    const result = await mlClient.selectFeatures({
      target: (ctx.params.target as string) ?? "msi",
      modality,
      n_top: (ctx.params.n_top_features as number) ?? 30,
    });
    panels.push({ modality, ...result });
  }

  return { feature_panels: panels };
}

export async function trainAndEvaluate(
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

  const result = await mlClient.classify({
    features: features.length > 0 ? features : "auto",
    target: (ctx.params.target as string) ?? "mismatch",
  });

  return { classification: result };
}

export async function matchCrossOmics(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.matchCrossOmics({
    dataset: (ctx.params.dataset as string) ?? "train",
  });
  return { cross_omics: result };
}

export async function runClassificationQC(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.classify({
    target: "mismatch",
    classifiers: (ctx.params.classification_methods as string[]) ?? [
      "ensemble",
    ],
  });
  return { classification_qc: result };
}

export async function runDistanceMatrix(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.matchCrossOmics({
    dataset: (ctx.params.dataset as string) ?? "train",
    n_iterations: (ctx.params.n_iterations as number) ?? 100,
  });
  return { distance_result: result };
}

export async function crossValidateFlags(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const classResult = ctx.results.get("classification") as Record<string, unknown> | undefined;
  const distResult = ctx.results.get("distance_matching") as Record<string, unknown> | undefined;

  return {
    concordance: {
      classification_flagged: classResult ?? {},
      distance_flagged: distResult ?? {},
    },
  };
}

export async function runPipeline(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.runPipeline({
    dataset: (ctx.params.dataset as string) ?? "train",
    target: (ctx.params.target as string) ?? "msi",
  });
  return { pipeline: result };
}

export async function dspyCompile(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.dspyBiomarkerDiscovery(ctx.params);
  return { dspy_compilation: result };
}
