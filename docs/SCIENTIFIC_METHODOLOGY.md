# Scientific Methodology

> This document describes the scientific methods implemented in the platform, grounded in the
> precisionFDA NCI-CPTAC Multi-Omics MSI Classification Challenge and the post-challenge
> COSMO collaboration among the top 3 teams.

---

## 1. Challenge Background

The precisionFDA Multi-Omics MSI Classification Challenge asked teams to:

1. Classify tumour samples by **microsatellite instability (MSI)** status using paired proteomics and RNA-Seq data from NCI-CPTAC clinical cohorts.
2. Detect **mislabeled or swapped samples** where molecular profiles contradict clinical annotations.

The challenge attracted 52 teams from 15 countries. After the competition, the top 3 teams (including the Sentieon 1st-place solution) collaborated to produce the **COSMO** (Cross-Omics Sample Matching and Omics) methodology, published in *Molecular & Cellular Proteomics*. This platform implements the COSMO-inspired pipeline as its core ML engine.

**Input data formats:**

| File | Format | Contents |
|------|--------|----------|
| `train_cli.tsv` / `test_cli.tsv` | TSV | Sample ID, MSI_status, gender |
| `train_pro.tsv` / `test_pro.tsv` | TSV | Genes (rows) x Samples (columns), protein expression |
| `train_rna.tsv` / `test_rna.tsv` | TSV | Genes (rows) x Samples (columns), transcript expression |

Data loading is handled by `OmicsDataLoader` (`core/data_loader.py`), which transposes molecular matrices to samples x genes and merges with clinical metadata.

---

## 2. The 4-Stage Pipeline

The `COSMOInspiredPipeline` (`core/pipeline.py`) implements a four-stage workflow:

```
Stage 1: Impute  -->  Stage 2: Match  -->  Stage 3: Predict  -->  Stage 4: Correct
```

### Stage 1: Imputation (`core/imputation.py`)

Multi-omics datasets routinely have 30%+ missing values. Naive filtering (drop genes with any NaN) discards critical signal. The championship approach distinguishes between two missingness mechanisms:

**MNAR (Missing Not At Random):**
- Y-chromosome genes (DDX3Y, EIF1AY, KDM5D, RPS4Y1, USP9Y, UTY, ZFY) are biologically absent in female samples.
- These are zero-filled, not imputed, because the absence is expected.

**MAR (Missing At Random):**
- All other missing values are assumed to be measurement artifacts.
- Imputed via **Non-negative Matrix Factorization (NMF)** with automatic rank selection.

**NMF imputation details:**
- Candidate ranks k in {2, 5, 8, 10, 15}
- Rank selected by masking 10% of observed values and minimizing reconstruction MSE
- `sklearn.decomposition.NMF` with `init="nndsvda"`, `max_iter=500`
- Non-negativity constraint (values clipped to >= 0)

After imputation, `AvailabilityFilter` (`core/availability.py`) compares gene counts before and after, reporting how many genes were "rescued" above the 90% availability threshold.

### Stage 2: Cross-Omics Matching (`core/cross_omics_matcher.py`)

This stage builds an independent, classification-free signal for mismatch detection by comparing each sample's proteomics and RNA-Seq profiles.

**Gene-level correlation analysis:**
- Per-gene linear regression: protein expression ~ RNA expression across shared samples
- Returns R-squared, slope, and intercept for each gene (minimum 3 valid pairs)

**Distance matrix construction** (two methods):
1. **Expression Rank**: `1 - |Spearman rho|` per sample across shared genes
2. **Linear Model**: Mean squared residuals from per-gene protein~RNA regressions

**Hungarian algorithm matching:**
- `scipy.optimize.linear_sum_assignment` on the NxN distance matrix
- Iterative subsampling: 100 iterations, each sampling 80% of genes
- Per-sample mismatch frequency across iterations
- Samples with mismatch frequency > 0.5 are flagged

### Stage 3: Feature Selection and Classification

**Feature selection** (`core/feature_selection.py`) uses four independent methods, then integrates:

| Method | Implementation | Key Parameters |
|--------|---------------|----------------|
| **ANOVA** | Per-gene one-way F-test | Bonferroni + Benjamini-Hochberg correction |
| **LASSO** | `LogisticRegressionCV(penalty="l1", solver="liblinear")` | Cross-validated C selection |
| **NSC** | Tibshirani's PAM (Nearest Shrunken Centroids) | Soft-thresholding with cross-validated delta |
| **Random Forest** | `GridSearchCV` over max_depth={3,5,10}, min_samples_leaf={1,3} | 500 trees, F1-weighted scoring |

**Ensemble integration** (`ensemble_select()`):
- `union_weighted` (default): Each method ranks its selected genes; final score = sum of 1/rank across methods. Top 30 genes retained.
- `intersection`: Only genes selected by all 4 methods.
- `union`: Genes selected by any method.

The output is a `FeaturePanel` dataclass containing `SelectedFeature` entries (name, score, method, p_value, rank) and a `method_agreement` dict showing which methods selected each gene.

**Classification** (`core/classifier.py`) builds an ensemble of 4 base classifiers:

| Classifier | Implementation | Notes |
|-----------|---------------|-------|
| **Label-Weighted k-NN** | k=min(5,3), inverse label-frequency weighting | Handles class imbalance without oversampling |
| **LASSO** | `LogisticRegressionCV(penalty="l1", solver="liblinear")` | L1 regularization for sparse solutions |
| **NSC-proxy** | `LogisticRegression(penalty="l2", solver="lbfgs")` | Centroid-inspired linear classifier |
| **Random Forest** | n_estimators=100, max_depth=5 | Non-linear feature interactions |

Each classifier is trained under two **phenotype strategies**:
- `separate_gender`: Classify gender only (binary)
- `separate_msi`: Classify MSI status only (binary)

This yields 8 base predictions (4 classifiers x 2 strategies), which are stacked into a **meta-learner** (LogisticRegression) via 5-fold StratifiedKFold cross-validation. The meta-learner produces final mismatch predictions with confidence scores.

### Stage 4: Dual Validation (`core/cross_omics_matcher.py`)

The most critical stage for trust. Flags from Stage 2 (distance matrix) and Stage 3 (classification) are cross-validated:

| Concordance Level | Condition | Action |
|-------------------|-----------|--------|
| **HIGH** | Flagged by both methods | High-confidence mismatch |
| **REVIEW** | Flagged by one method only | Requires expert review |
| **PASS** | Flagged by neither | Sample passes QC |

This dual-method approach addresses the core trust problem: a researcher is far more likely to accept a mismatch call when two independent analytical paths agree.

---

## 3. Key Findings

### S100A14 as Dominant MSI Predictor

S100A14 emerged as the top biomarker across both modalities with a Random Forest importance score of 0.318 (highest among all genes). It appears in:
- precisionFDA top-5 proteomics panel
- Full 26-gene proteomics MSI signature
- Full 26-gene RNA-Seq MSI signature

### Immune Pathway Enrichment

The MSI gene signatures are heavily enriched for immune-related pathways, consistent with the established biology of MSI-High tumours (high neoantigen load -> immune infiltration):

| Pathway | Genes | Biological Basis |
|---------|-------|-----------------|
| **Immune infiltration** | PTPRC, ITGB2, LCP1, NCF2 | Leukocyte markers elevated in MSI-H tumours |
| **Interferon response** | GBP1, GBP4, IRF1, IFI35, WARS | Interferon-gamma signalling upregulated by neoantigens |
| **Antigen presentation** | TAP1, TAPBP, LAG3 | MHC-I pathway components amplified in MSI-H |
| **Mismatch repair adjacent** | CIITA, TYMP | Genomic neighbours of MMR genes, co-regulated |

These 14 pathway markers serve as the ground truth for the `BiologicalValidityEval`.

### Published Gene Panels

From the challenge results, the platform validates against these reference panels:

| Panel | Genes | Source |
|-------|-------|--------|
| precisionFDA top-5 proteomics | S100A14, ROCK2, FHDC1, PGM2, GAR1 | Top RF importance from original analysis |
| precisionFDA MSI proteomics | 26 genes (TAP1, LCP1, PTPN6, NCF2, GBP4, WARS, ...) | Full proteomics signature |
| precisionFDA MSI RNA-Seq | 26 genes (EPDR1, APOL3, POU5F1B, MMP7, S100A14, ...) | Full transcriptomics signature |
| Gender proteomics | 7 Y-chromosome + XIST, KDM5C | Sex-linked expression markers |
| Gender RNA-Seq | 7 Y-chromosome + XIST, TSIX | Sex-linked expression markers |

---

## 4. Evaluation Framework

Each eval returns an `EvalResult(name, passed, score, threshold, details)` dataclass.

### Biological Validity (`evals/biological_validity.py`)

Loads pathway markers from `evals/fixtures/known_msi_signatures.json` and scores the fraction of pathways with at least one gene represented in the agent-selected panel.

- **Threshold**: >= 0.60 (60% pathway coverage)
- **Fixture**: 4 pathways with 14 total genes
- **Score**: pathways_covered / total_pathways

### Hallucination Detection (`evals/hallucination_detection.py`)

Verifies that PubMed IDs cited in agent-generated explanations actually exist by querying NCBI E-utilities.

- **Threshold**: >= 0.90 (90% verifiable citations)
- **Mitigation**: The `LiteratureGroundingSkill` pre-grounds all gene explanations in real PubMed results before the agent presents them

### Reproducibility (`evals/reproducibility.py`)

Runs the pipeline multiple times with identical inputs and measures consistency of feature selection.

- **Metric**: Pairwise Jaccard similarity of top-20 selected features
- **Threshold**: >= 0.85 average Jaccard across runs

### Benchmark Comparison (`evals/benchmark_comparison.py`)

Compares the agent-selected gene panel against published reference panels (precisionFDA results, TCGA MSI signatures, Guinney CMS markers).

- **Metrics**: Jaccard overlap, unique discoveries, shared genes
- **Purpose**: Validates competitiveness with established results

---

## 5. Methodological Choices and Rationale

### Why NMF Over Simple Median Imputation?

Median imputation destroys covariance structure between genes. NMF preserves latent factor relationships by decomposing the expression matrix into non-negative components. The championship solution showed NMF rescues genes that would otherwise be filtered, expanding the available feature space by up to 40%.

### Why 4 Feature Selection Methods?

Single-method selection is unstable in high-dimensional, low-N settings (typical of clinical omics: ~50-200 samples, ~5000-20000 genes). Each method has different biases:
- ANOVA finds univariate separators but misses interactions
- LASSO finds sparse linear combinations but struggles with correlated features
- NSC is optimal for high-dimensional low-N but assumes class-conditional normality
- Random Forest captures non-linear interactions but is sensitive to hyperparameters

The `union_weighted` integration reduces individual method variance while preserving sensitivity.

### Why Dual-Method Mismatch Detection?

Classification-based detection (Stage 3) captures complex phenotype-expression relationships but can overfit. Distance-matrix matching (Stage 2) is model-free and robust to label noise but less sensitive to subtle mismatches. Requiring concordance between both methods reduces false positives — the key concern for researchers who will act on QC flags.

### Why the Hungarian Algorithm?

The optimal assignment problem (matching N proteomics profiles to N RNA-Seq profiles) is naturally solved by the Hungarian algorithm in O(N^3). Iterative subsampling adds robustness by preventing any single gene set from dominating the assignment.

### Why Label-Weighted k-NN?

MSI-High samples represent roughly 15% of clinical cohorts. Standard k-NN assigns equal weight to all neighbours, biasing toward the majority class. Inverse label-frequency weighting upweights rare-class neighbours, improving recall without oversampling.
