/**
 * Agent skill: End-to-end biomarker discovery workflow.
 * Migrated from agent_skills/biomarker_discovery.py.
 *
 * Orchestrates: load -> impute -> availability -> select -> classify -> match -> explain
 */

import * as mlClient from "@/lib/ml-client";
import Anthropic from "@anthropic-ai/sdk";

export interface BiomarkerDiscoveryConfig {
  dataset?: string;
  target?: string;
  modalities?: string[];
  impute_strategy?: string;
  availability_threshold?: number;
  integration?: string;
  n_top?: number;
  cv_folds?: number;
  distance_method?: string;
  n_iterations?: number;
  gene_sampling_fraction?: number;
  classification_target?: string;
  phenotype_strategy?: string;
  data_dir?: string;
  enable_slm_routing?: boolean;
}

export async function runBiomarkerDiscovery(
  config: BiomarkerDiscoveryConfig = {},
): Promise<Record<string, unknown>> {
  const target = config.target ?? "msi";
  const modalities = config.modalities ?? ["proteomics", "rnaseq"];
  const dataset = config.dataset ?? "train";
  const report: Record<string, unknown> = {
    target,
    modalities,
    steps: {},
  };
  const steps: Record<string, unknown> = {};

  // Step 1: Impute per modality
  const imputeResults: Record<string, unknown> = {};
  for (const modality of modalities) {
    imputeResults[modality] = await mlClient.impute({
      dataset,
      modality,
      strategy: config.impute_strategy ?? "nmf",
      classify_missingness: true,
    });
  }
  steps.impute_missing = imputeResults;

  // Step 2: Select biomarkers per modality
  const selectionResults: Record<string, unknown> = {};
  const allGenes: string[] = [];
  for (const modality of modalities) {
    const result = await mlClient.selectFeatures({
      target,
      modality,
      integration: config.integration ?? "union_weighted",
      n_top: config.n_top ?? 30,
    });
    selectionResults[modality] = result;
    for (const biomarker of result.biomarkers ?? []) {
      const gene = (biomarker as Record<string, unknown>).gene as string;
      if (gene && !allGenes.includes(gene)) allGenes.push(gene);
    }
  }
  steps.select_biomarkers = selectionResults;

  // Step 3: Classification
  const classifyResult = await mlClient.classify({
    target: config.classification_target ?? "mismatch",
    classifiers: "ensemble",
    phenotype_strategy: config.phenotype_strategy ?? "both",
    cv_folds: config.cv_folds ?? 10,
  });
  steps.run_classification = classifyResult;

  // Step 4: Cross-omics matching
  const matchResult = await mlClient.matchCrossOmics({
    dataset,
    distance_method: config.distance_method ?? "both",
    n_iterations: config.n_iterations ?? 100,
    gene_sampling_fraction: config.gene_sampling_fraction ?? 0.8,
  });
  steps.match_cross_omics = matchResult;

  // Step 5: Explain top features via Claude
  if (allGenes.length > 0) {
    const client = new Anthropic();
    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 2048,
      messages: [
        {
          role: "user",
          content: `Explain the biological relevance of these biomarker genes for ${target} classification in colorectal cancer: ${allGenes.slice(0, 30).join(", ")}. For each gene provide: function, ${target} relevance, pathways, clinical significance.`,
        },
      ],
    });
    steps.explain_features = {
      genes: allGenes.slice(0, 30),
      explanation:
        message.content[0].type === "text" ? message.content[0].text : "",
    };
  }

  report.steps = steps;
  report.summary = {
    n_features_selected: allGenes.length,
    ensemble_f1: classifyResult.ensemble_f1,
    n_mismatches: matchResult.identified_mismatches.length,
  };

  return report;
}
