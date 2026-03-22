/**
 * TypeScript workflow engine — state machine orchestrator.
 * Replaces workflows/local_runner.py.
 *
 * Each workflow is a sequence of phases. Each phase calls an activity
 * (which may proxy to the Python ML service or call Claude directly).
 * Progress is persisted to PostgreSQL via Prisma.
 */

import { updateProgress } from "./progress";
import type {
  WorkflowContext,
  WorkflowDefinition,
  WorkflowType,
} from "./types";
import * as mlActivities from "./activities/ml";
import * as claudeActivities from "./activities/claude";
import * as dataActivities from "./activities/data";

// --- Workflow Definitions ---

const biomarkerDiscoveryWorkflow: WorkflowDefinition = {
  type: "biomarker_discovery",
  phases: [
    { name: "data_loading", activity: dataActivities.loadAndValidate },
    { name: "imputation", activity: mlActivities.imputeData },
    { name: "feature_selection", activity: mlActivities.selectFeatures },
    { name: "classification", activity: mlActivities.trainAndEvaluate },
    { name: "cross_omics", activity: mlActivities.matchCrossOmics },
    { name: "interpretation", activity: claudeActivities.generateInterpretation },
  ],
};

const sampleQcWorkflow: WorkflowDefinition = {
  type: "sample_qc",
  phases: [
    { name: "data_loading", activity: dataActivities.loadClinical },
    { name: "classification", activity: mlActivities.runClassificationQC },
    { name: "distance_matching", activity: mlActivities.runDistanceMatrix },
    { name: "concordance", activity: mlActivities.crossValidateFlags },
  ],
};

const WORKFLOW_REGISTRY: Record<WorkflowType, WorkflowDefinition> = {
  biomarker_discovery: biomarkerDiscoveryWorkflow,
  sample_qc: sampleQcWorkflow,
  prompt_optimization: {
    type: "prompt_optimization",
    phases: [
      { name: "synthetic_cohort", activity: dataActivities.generateSynthetic },
      { name: "baseline_run", activity: mlActivities.runPipeline },
      { name: "dspy_compile", activity: mlActivities.dspyCompile },
      { name: "optimized_run", activity: mlActivities.runPipeline },
    ],
  },
  cosmo_pipeline: {
    type: "cosmo_pipeline",
    phases: [
      { name: "data_loading", activity: dataActivities.loadAndValidate },
      { name: "imputation", activity: mlActivities.imputeData },
      { name: "feature_selection", activity: mlActivities.selectFeatures },
      { name: "classification", activity: mlActivities.trainAndEvaluate },
      { name: "cross_omics", activity: mlActivities.matchCrossOmics },
      { name: "interpretation", activity: claudeActivities.generateInterpretation },
    ],
  },
};

// --- Engine ---

export async function executeWorkflow(
  workflowId: string,
  workflowType: WorkflowType,
  params: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const definition = WORKFLOW_REGISTRY[workflowType];
  if (!definition) {
    throw new Error(`Unknown workflow type: ${workflowType}`);
  }

  const ctx: WorkflowContext = {
    workflowId,
    workflowType,
    params,
    results: new Map(),
  };

  await updateProgress(workflowId, { status: "running" });

  try {
    for (const phase of definition.phases) {
      await updateProgress(workflowId, { currentPhase: phase.name });

      const result = await phase.activity(ctx);
      ctx.results.set(phase.name, result);

      await updateProgress(workflowId, { phaseCompleted: phase.name });
    }

    const finalResult = Object.fromEntries(ctx.results);
    await updateProgress(workflowId, {
      status: "completed",
      result: finalResult,
    });

    return {
      workflow_id: workflowId,
      status: "completed",
      ...finalResult,
    };
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err);
    await updateProgress(workflowId, { status: "failed", error });
    throw err;
  }
}
