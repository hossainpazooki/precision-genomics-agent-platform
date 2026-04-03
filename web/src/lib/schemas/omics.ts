import { z } from "zod";

// --- 1. Load Dataset ---
export const LoadDatasetInput = z.object({
  dataset: z.string().default("train"),
  modalities: z.array(z.string()).default(["clinical", "proteomics", "rnaseq"]),
  data_dir: z.string().nullable().optional(),
});
export type LoadDatasetInput = z.infer<typeof LoadDatasetInput>;

export const LoadDatasetOutput = z.object({
  samples: z.number().int(),
  features: z.record(z.number()),
  msi_distribution: z.record(z.number()),
  gender_distribution: z.record(z.number()),
  missing_data_summary: z.record(z.number()),
});
export type LoadDatasetOutput = z.infer<typeof LoadDatasetOutput>;

// --- 2. Impute Missing ---
export const ImputeMissingInput = z.object({
  dataset: z.string().default("train"),
  modality: z.string().default("proteomics"),
  strategy: z.string().default("nmf"),
  classify_missingness: z.boolean().default(true),
});
export type ImputeMissingInput = z.infer<typeof ImputeMissingInput>;

export const ImputeMissingOutput = z.object({
  genes_before: z.number().int(),
  genes_imputed_mar: z.number().int(),
  genes_assigned_mnar_zero: z.number().int(),
  nmf_reconstruction_error: z.number(),
  features_recovered: z.number().int(),
  comparison: z.record(z.number()),
});
export type ImputeMissingOutput = z.infer<typeof ImputeMissingOutput>;

// --- 3. Check Availability ---
export const CheckAvailabilityInput = z.object({
  genes: z.array(z.string()).nullable().optional(),
  threshold: z.number().default(0.9),
  dataset: z.string().default("train"),
  use_imputed: z.boolean().default(true),
});
export type CheckAvailabilityInput = z.infer<typeof CheckAvailabilityInput>;

export const CheckAvailabilityOutput = z.object({
  available: z.array(z.string()),
  filtered: z.array(z.string()),
  availability_scores: z.record(z.number()),
  imputation_impact: z.record(z.number()),
});
export type CheckAvailabilityOutput = z.infer<typeof CheckAvailabilityOutput>;

// --- 4. Select Biomarkers ---
export const SelectBiomarkersInput = z.object({
  target: z.string().default("msi"),
  modality: z.string().default("proteomics"),
  methods: z.union([z.array(z.string()), z.string()]).default("all"),
  integration: z.string().default("union_weighted"),
  n_top: z.number().int().default(30),
  p_value_correction: z.string().default("both"),
});
export type SelectBiomarkersInput = z.infer<typeof SelectBiomarkersInput>;

export const SelectBiomarkersOutput = z.object({
  biomarkers: z.array(z.record(z.unknown())),
  method_agreement: z.record(z.array(z.string())),
  comparison_to_original: z.record(z.number()),
});
export type SelectBiomarkersOutput = z.infer<typeof SelectBiomarkersOutput>;

// --- 5. Run Classification ---
export const RunClassificationInput = z.object({
  features: z.union([z.array(z.string()), z.string()]).default("auto"),
  target: z.string().default("mismatch"),
  classifiers: z.union([z.array(z.string()), z.string()]).default("ensemble"),
  phenotype_strategy: z.string().default("both"),
  meta_learner: z.string().default("logistic_regression"),
  test_size: z.number().default(0.3),
  cv_folds: z.number().int().default(10),
});
export type RunClassificationInput = z.infer<typeof RunClassificationInput>;

export const RunClassificationOutput = z.object({
  ensemble_f1: z.number(),
  per_classifier_f1: z.record(z.number()),
  best_strategy: z.string(),
  strategy_comparison: z.record(z.number()),
  feature_importances: z.array(z.record(z.unknown())),
  comparison_to_baseline: z.record(z.number()),
});
export type RunClassificationOutput = z.infer<typeof RunClassificationOutput>;

// --- 6. Match Cross-Omics ---
export const MatchCrossOmicsInput = z.object({
  dataset: z.string().default("train"),
  distance_method: z.string().default("both"),
  n_iterations: z.number().int().default(100),
  gene_sampling_fraction: z.number().default(0.8),
});
export type MatchCrossOmicsInput = z.infer<typeof MatchCrossOmicsInput>;

export const MatchCrossOmicsOutput = z.object({
  distance_matrix_info: z.record(z.unknown()),
  identified_mismatches: z.array(z.record(z.unknown())),
  iteration_agreement: z.number(),
});
export type MatchCrossOmicsOutput = z.infer<typeof MatchCrossOmicsOutput>;

// --- 7. Evaluate Model ---
export const EvaluateModelInput = z.object({
  model_id: z.string().default("ensemble"),
  test_data: z.string().default("holdout"),
  compare_to_baseline: z.boolean().default(true),
});
export type EvaluateModelInput = z.infer<typeof EvaluateModelInput>;

export const EvaluateModelOutput = z.object({
  f1_score: z.number(),
  precision: z.number(),
  recall: z.number(),
  confusion_matrix: z.array(z.unknown()),
  roc_auc: z.number(),
  baseline_comparison: z.record(z.number()),
});
export type EvaluateModelOutput = z.infer<typeof EvaluateModelOutput>;

// --- 8. Explain Features ---
export const ExplainFeaturesInput = z.object({
  genes: z.array(z.string()),
  context: z.string().default("msi_classification"),
  include_provenance: z.boolean().default(true),
});
export type ExplainFeaturesInput = z.infer<typeof ExplainFeaturesInput>;

export const ExplainFeaturesOutput = z.object({
  explanations: z.array(z.record(z.unknown())),
});
export type ExplainFeaturesOutput = z.infer<typeof ExplainFeaturesOutput>;

// --- 9. Explain Features (Local SLM) ---
export const ExplainFeaturesLocalInput = z.object({
  genes: z.array(z.string()),
  context: z.string().default("msi_classification"),
  target: z.string().default("msi"),
});
export type ExplainFeaturesLocalInput = z.infer<
  typeof ExplainFeaturesLocalInput
>;
