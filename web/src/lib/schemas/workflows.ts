import { z } from "zod";

export const WorkflowStatus = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
]);
export type WorkflowStatus = z.infer<typeof WorkflowStatus>;

// --- Biomarker Discovery ---

export const BiomarkerDiscoveryParams = z.object({
  dataset: z.string().default("train"),
  target: z.string().default("msi"),
  modalities: z.array(z.string()).default(["proteomics", "rnaseq"]),
  n_top_features: z.number().int().default(30),
  cv_folds: z.number().int().default(10),
});
export type BiomarkerDiscoveryParams = z.infer<typeof BiomarkerDiscoveryParams>;

export const BiomarkerDiscoveryResult = z.object({
  workflow_id: z.string(),
  status: WorkflowStatus,
  started_at: z.string().datetime(),
  completed_at: z.string().datetime().nullable().optional(),
  target: z.string(),
  modalities: z.array(z.string()),
  feature_panel: z.record(z.unknown()).default({}),
  classification_metrics: z.record(z.unknown()).default({}),
  cross_omics_validation: z.record(z.unknown()).default({}),
  interpretation: z.record(z.unknown()).default({}),
  error: z.string().nullable().optional(),
});
export type BiomarkerDiscoveryResult = z.infer<typeof BiomarkerDiscoveryResult>;

export const BiomarkerDiscoveryProgress = z.object({
  workflow_id: z.string(),
  status: WorkflowStatus,
  current_phase: z.string().default("pending"),
  phases_completed: z.array(z.string()).default([]),
  phases_remaining: z.array(z.string()).default([]),
});
export type BiomarkerDiscoveryProgress = z.infer<
  typeof BiomarkerDiscoveryProgress
>;

// --- Sample QC ---

export const SampleQCParams = z.object({
  dataset: z.string().default("train"),
  classification_methods: z.array(z.string()).default(["ensemble"]),
  distance_methods: z.array(z.string()).default(["hungarian"]),
  n_iterations: z.number().int().default(100),
});
export type SampleQCParams = z.infer<typeof SampleQCParams>;

export const SampleQCResult = z.object({
  workflow_id: z.string(),
  status: WorkflowStatus,
  started_at: z.string().datetime(),
  completed_at: z.string().datetime().nullable().optional(),
  total_samples: z.number().int().default(0),
  flagged_samples: z.array(z.record(z.unknown())).default([]),
  concordance_report: z.record(z.unknown()).default({}),
  error: z.string().nullable().optional(),
});
export type SampleQCResult = z.infer<typeof SampleQCResult>;

export const SampleQCProgress = z.object({
  workflow_id: z.string(),
  status: WorkflowStatus,
  current_phase: z.string().default("pending"),
  samples_processed: z.number().int().default(0),
  total_samples: z.number().int().default(0),
});
export type SampleQCProgress = z.infer<typeof SampleQCProgress>;

// --- Generic Workflow ---

export const WorkflowInfo = z.object({
  workflow_id: z.string(),
  workflow_type: z.string(),
  status: WorkflowStatus,
  started_at: z.string().datetime(),
  completed_at: z.string().datetime().nullable().optional(),
  run_id: z.string().nullable().optional(),
  execution_name: z.string().nullable().optional(),
});
export type WorkflowInfo = z.infer<typeof WorkflowInfo>;

// --- Run Workflow Request ---

export const RunWorkflowRequest = z.object({
  workflow_type: z.enum(["biomarker_discovery", "sample_qc"]),
  params: z.record(z.unknown()).default({}),
});
export type RunWorkflowRequest = z.infer<typeof RunWorkflowRequest>;
