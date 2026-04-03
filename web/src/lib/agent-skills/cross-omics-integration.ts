/**
 * Agent skill: Cross-omics integration pipeline.
 * Migrated from agent_skills/cross_omics_integration.py.
 */

import * as mlClient from "@/lib/ml-client";

export interface CrossOmicsConfig {
  dataset?: string;
  target?: string;
  impute_strategy?: string;
  availability_threshold?: number;
  distance_method?: string;
  n_iterations?: number;
  gene_sampling_fraction?: number;
  cv_folds?: number;
  test_data?: string;
}

export async function runCrossOmicsIntegration(
  config: CrossOmicsConfig = {},
): Promise<Record<string, unknown>> {
  const dataset = config.dataset ?? "train";
  const steps: Record<string, unknown> = {};

  // Step 1: Impute both modalities
  for (const modality of ["proteomics", "rnaseq"] as const) {
    steps[`impute_${modality}`] = await mlClient.impute({
      dataset,
      modality,
      strategy: config.impute_strategy ?? "nmf",
    });
  }

  // Step 2: Cross-omics matching
  const matchResult = await mlClient.matchCrossOmics({
    dataset,
    distance_method: config.distance_method ?? "both",
    n_iterations: config.n_iterations ?? 100,
    gene_sampling_fraction: config.gene_sampling_fraction ?? 0.8,
  });
  steps.match_cross_omics = matchResult;

  // Step 3: Classification on integrated features
  const classifyResult = await mlClient.classify({
    target: config.target ?? "mismatch",
    classifiers: "ensemble",
    phenotype_strategy: "both",
    cv_folds: config.cv_folds ?? 10,
  });
  steps.run_classification = classifyResult;

  // Step 4: Evaluation
  const evalResult = await mlClient.evaluate({
    model_id: "ensemble",
    test_data: config.test_data ?? "holdout",
    compare_to_baseline: true,
  });
  steps.evaluate_model = evalResult;

  return {
    dataset,
    steps,
    summary: {
      n_mismatches: matchResult.identified_mismatches.length,
      iteration_agreement: matchResult.iteration_agreement,
      ensemble_f1: classifyResult.ensemble_f1,
      eval_f1: evalResult.f1_score,
    },
  };
}
