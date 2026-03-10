# Technical Writeup: Precision Genomics Agent Platform

## Problem Statement

As precision medicine expands beyond single-omics analysis, integrating proteomics, transcriptomics, and clinical data introduces a critical quality problem: sample mislabeling. When patient samples are accidentally swapped across data modalities, downstream biomarker discovery produces misleading results that can affect treatment decisions. The NCI-CPTAC precisionFDA challenge formalized this problem, providing a dataset of 80 tumor samples with intentionally introduced mislabels across paired proteomics (~7K genes) and RNA-Seq (~15K genes) measurements.

This platform addresses both the mislabeling detection problem and the downstream task of MSI (microsatellite instability) status classification — a biomarker increasingly used to guide immunotherapy selection.

## Methodology

### COSMO-Inspired Pipeline

The core analysis follows a four-stage pipeline inspired by the COSMO (Cross-Omics Sample Matching for Omics) approach:

**Stage 1 — Imputation.** Missing values in omics data fall into two categories: MNAR (missing-not-at-random, typically below detection limits) and MAR (missing-at-random, from batch effects). The imputer classifies each missing value and applies minimum-value imputation for MNAR and NMF-based matrix completion for MAR, with automatic rank selection. Y-chromosome genes receive gender-stratified handling to avoid introducing biological artifacts.

**Stage 2 — Cross-Omics Matching.** Proteomics and RNA-Seq samples are aligned using Spearman correlation across shared genes, producing a distance matrix solved by the Hungarian algorithm for optimal assignment. This identifies samples whose molecular profiles are discordant across modalities — the hallmark of mislabeling.

**Stage 3 — Feature Selection & Classification.** Four independent feature selection methods (ANOVA F-test, LASSO L1, NSC soft thresholding, Random Forest importance) vote on the final biomarker panel. The ensemble reduces method-specific bias. An ensemble classifier (logistic regression + random forest + gradient boosting) with a meta-learner combines separate-target (gender alone, MSI alone) and joint-target (4-class combined phenotype) predictions.

**Stage 4 — Dual Validation.** Proteomics-only and RNA-Seq-only predictions are compared. Concordant predictions receive HIGH confidence; discordant predictions are flagged for REVIEW. This dual-path approach catches cases where a mislabel affects only one modality.

### Joint Phenotype Strategy

A key technical contribution is the joint phenotype classification strategy. Rather than predicting gender and MSI independently (separate strategy), the classifier also trains on the 4-class joint label (gender × MSI). This captures interaction effects — for example, some MSI pathway genes show gender-dependent expression. The meta-learner receives predictions from both strategies, learning when joint prediction improves over separate prediction.

### Agent Architecture

The platform implements a layered agent architecture:

- **Skill Layer** — Domain-specific async Python classes (biomarker discovery, sample QC, cross-omics integration) that orchestrate multi-step analysis through MCP tool calls
- **MCP Tool Layer** — 9 protocol-compliant tools with Pydantic validation, providing a standardized interface between agent reasoning and computation
- **Core ML Layer** — Pure computation classes with no I/O dependencies, enabling testing without infrastructure
- **Workflow Layer** — GCP Workflows YAML definitions for production durability, with a local runner for development

This separation means the same analysis logic works in three contexts: interactive agent sessions (skills), production pipelines (workflows), and automated testing (direct core class calls).

## Architecture Decisions

**GCP Workflows over Temporal.** The platform originally used Temporal for workflow orchestration on a self-managed GCE VM (~$98/month). Since the workflows are medium-complexity sequential pipelines without long-running replay or signal requirements, we migrated to GCP Workflows (~$6/month), eliminating VM management overhead and aligning with the serverless architecture. Activities are exposed as HTTP endpoints on a dedicated Cloud Run service.

**MCP for tool boundaries.** The Model Context Protocol provides schema validation at the boundary between agent reasoning and computation. This is important for genomics tools where input validation (e.g., ensuring gene names are from the correct organism, modality types are valid) prevents silent errors that could propagate through the pipeline.

**Synthetic data for testing.** The platform includes a configurable synthetic data generator with five signal layers (MSI pathway fold-changes, gender-dependent expression, cross-omics shared factors, mislabel injection, structured missingness). This enables comprehensive testing without committing real patient data, while producing datasets with realistic characteristics that exercise the full pipeline.

**DSPy for prompt optimization.** Four domain-specific modules (biomarker discovery, feature interpretation, sample QC, regulatory reporting) are compiled with MIPROv2 to automatically optimize prompts against evaluation metrics. This replaces manual prompt engineering with systematic optimization.

## Evaluation Framework

Trust in AI-assisted biomarker discovery requires domain-specific evaluation beyond standard ML metrics:

- **Biological Validity** (>= 60% pathway coverage) — Measures whether agent-selected genes overlap with known MSI pathway markers (immune infiltration, interferon response, antigen presentation, mismatch repair adjacent)
- **Hallucination Detection** (>= 90% citation accuracy) — Verifies PubMed citations in biological interpretations are real and relevant
- **Reproducibility** (>= 85% Jaccard similarity) — Ensures consistent feature selection across repeated runs
- **Benchmark Comparison** — Compares selected biomarker panels against published signatures

These evals are CI-gatable: each returns a pass/fail result with a numeric score, enabling automated quality gates in deployment pipelines.

## Lessons Learned

**1. Missing data classification matters more than imputation method.** The choice between MNAR and MAR imputation had a larger impact on downstream classification than the specific imputation algorithm. Getting the classification wrong (e.g., treating below-detection-limit zeros as random missingness) introduced systematic bias in feature selection.

**2. Cross-omics concordance is a powerful validation signal.** When proteomics and RNA-Seq independently agree on a prediction, confidence is substantially higher than either modality alone. This dual-path validation is especially valuable for sample mislabeling detection, where the mislabel may affect only one modality.

**3. Joint phenotype improves over separate prediction.** The 4-class joint label (gender × MSI) captures interaction effects that separate binary classifiers miss. The meta-learner learned to weight joint predictions more heavily when the sample falls near decision boundaries.

**4. Serverless workflows reduce operational burden significantly.** Moving from a self-managed Temporal VM to GCP Workflows eliminated a class of operational issues (VM monitoring, Docker updates, Temporal version management) while reducing cost by ~94%. The tradeoff — less expressive orchestration — was acceptable because the workflows are straightforward sequential pipelines.

**5. Synthetic data generators need realistic structure, not just random noise.** Early synthetic datasets with uniform random noise produced unrealistically high classifier accuracy. Adding structured signal layers (pathway fold-changes, gender effects, batch dropout missingness) produced datasets that exercised edge cases the pipeline needed to handle.

## Future Directions

- **Active learning loop**: Use classifier uncertainty to prioritize manual review of ambiguous samples
- **Longitudinal monitoring**: Track biomarker panel stability across dataset updates using the feature snapshot infrastructure
- **Multi-center validation**: Extend the synthetic data generator with site-specific batch effects to test generalization
- **Regulatory documentation**: Expand the DSPy regulatory report module to generate IVD-ready documentation
