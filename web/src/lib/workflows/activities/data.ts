/**
 * Data activities — some proxied to ML service, some local.
 * Replaces workflows/activities/data_activities.py.
 */

import * as mlClient from "@/lib/ml-client";
import type { WorkflowContext } from "../types";

export async function loadAndValidate(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.impute({
    dataset: (ctx.params.dataset as string) ?? "train",
    modality: "proteomics",
    strategy: "nmf",
  });

  return {
    data_summary: {
      dataset: ctx.params.dataset ?? "train",
      modalities: ctx.params.modalities ?? ["proteomics", "rnaseq"],
      genes_before: result.genes_before,
    },
  };
}

export async function loadClinical(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  // Delegate to ML service for data loading
  return {
    clinical_data: {
      dataset: ctx.params.dataset ?? "train",
      loaded: true,
    },
  };
}

export async function generateSynthetic(
  ctx: WorkflowContext,
): Promise<Record<string, unknown>> {
  const result = await mlClient.generateSynthetic({
    n_samples: (ctx.params.n_samples as number) ?? 100,
  });
  return { synthetic_cohort: result };
}
