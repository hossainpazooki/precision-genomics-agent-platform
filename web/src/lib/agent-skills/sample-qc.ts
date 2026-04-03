/**
 * Agent skill: Sample QC and mismatch detection.
 * Migrated from agent_skills/sample_qc.py.
 *
 * Dual-path: classification-based + distance-matrix matching.
 */

import * as mlClient from "@/lib/ml-client";

export interface SampleQCConfig {
  dataset?: string;
  impute_strategy?: string;
  cv_folds?: number;
  distance_method?: string;
  n_iterations?: number;
  gene_sampling_fraction?: number;
}

export async function runSampleQC(
  config: SampleQCConfig = {},
): Promise<Record<string, unknown>> {
  const dataset = config.dataset ?? "train";
  const report: Record<string, unknown> = { dataset, paths: {} };
  const paths: Record<string, unknown> = {};

  // Impute before analysis
  await mlClient.impute({
    dataset,
    modality: "proteomics",
    strategy: config.impute_strategy ?? "nmf",
  });

  // Path A: Classification-based mismatch detection
  const classifyResult = await mlClient.classify({
    target: "mismatch",
    classifiers: "ensemble",
    phenotype_strategy: "both",
    cv_folds: config.cv_folds ?? 10,
  });
  paths.classification = {
    ensemble_f1: classifyResult.ensemble_f1,
    per_classifier_f1: classifyResult.per_classifier_f1,
    best_strategy: classifyResult.best_strategy,
  };

  // Path B: Cross-omics distance matching
  const matchResult = await mlClient.matchCrossOmics({
    dataset,
    distance_method: config.distance_method ?? "both",
    n_iterations: config.n_iterations ?? 100,
    gene_sampling_fraction: config.gene_sampling_fraction ?? 0.8,
  });
  paths.distance_matrix = {
    distance_matrix_info: matchResult.distance_matrix_info,
    identified_mismatches: matchResult.identified_mismatches,
    iteration_agreement: matchResult.iteration_agreement,
  };

  report.paths = paths;

  // Cross-validate
  const flaggedIds = new Set(
    matchResult.identified_mismatches
      .map((m) => (m as Record<string, unknown>).sample_id as string)
      .filter(Boolean),
  );

  report.concordance = {
    classification_f1: classifyResult.ensemble_f1,
    flagged_by_distance: [...flaggedIds].sort(),
    n_flagged_distance: flaggedIds.size,
    iteration_agreement: matchResult.iteration_agreement,
  };

  // Verdict
  if (flaggedIds.size === 0) {
    report.verdict = "PASS";
    report.confidence = "high";
  } else if (flaggedIds.size <= 2) {
    report.verdict = "WARNING";
    report.confidence = "medium";
  } else {
    report.verdict = "FAIL";
    report.confidence = "high";
  }

  return report;
}
