# Synthetic Data Generation Strategy

**Precision Genomics Agent Platform**
**Author:** Hossain | **Date:** February 2026

> **✅ STATUS: IMPLEMENTED — March 2026**
>
> The synthetic data generation system has been implemented in `core/synthetic.py` as the `SyntheticCohortGenerator` class. It supports MSI/gender signal injection, cross-omics concordance, mislabel injection, structured missingness (MNAR + MAR), and presets (`unit`, `integration`, `benchmark`). 11 tests passing in `tests/test_core/test_synthetic.py`.

---

## Motivation

The current `conftest.py` fixtures generate structurally valid data (correct schema, sample IDs, gene names) but lack the biological signal structure the pipeline depends on. A log-normal draw with random NaN injection produces expression matrices where ANOVA finds nothing, LASSO selects noise, and cross-omics matching returns random correlations. The pipeline "works" on this data — but it can't demonstrate that it works *correctly*.

A production-grade synthetic data generator needs to plant known ground truth across five dimensions: MSI phenotype signal, gender signal, cross-omics concordance, mislabeling events, and missing data patterns. This lets every evaluation have a verifiable expected answer.

> **Existing Work:** The current `conftest.py` already provides basic synthetic data fixtures with log-normal expression distributions, Y-chromosome NaN injection for female samples, and gene panels drawn from `core/constants.py`. This document proposes a significantly more sophisticated generator that adds biological signal structure (MSI phenotype, pathway correlations, cross-omics concordance, structured missingness) beyond what the current fixtures provide.

---

## Architecture: `core/synthetic.py`

A single module with a top-level `SyntheticCohortGenerator` class that produces a complete multi-omics dataset as a dictionary of DataFrames. All randomness flows through a single `numpy.random.Generator` seeded at construction time.

```
SyntheticCohortGenerator
├── generate_cohort() → dict[str, pd.DataFrame]
│   ├── _generate_clinical()
│   ├── _generate_proteomics()
│   ├── _generate_rnaseq()
│   ├── _inject_mislabels()
│   └── _inject_missingness()
└── get_ground_truth() → dict
```

**Output contract:**

```python
{
    "clinical": pd.DataFrame,       # sample_id, MSI_status, gender
    "proteomics": pd.DataFrame,     # samples × genes (float, with NaN)
    "rnaseq": pd.DataFrame,         # samples × genes (float, with NaN)
    "ground_truth": {
        "mislabeled_samples": list[str],
        "mislabel_type": dict[str, str],   # sample_id → "proteomics" | "rnaseq" | "clinical"
        "swap_pairs": list[tuple[str, str]],
        "msi_h_samples": list[str],
        "gender_map": dict[str, str],
    }
}
```

---

## Layer 1: Biological Signal Injection

### 1.1 MSI Phenotype Signal

MSI-H tumors have elevated immune infiltration, interferon response, and antigen presentation genes. The generator needs to encode this as a measurable expression shift in the known MSI panel genes.

**Strategy — Phenotype-conditioned expression:**

```python
# Base expression for all genes: log-normal
base = rng.lognormal(mean=2.0, sigma=1.2, size=(n_samples, n_genes))

# MSI signal: for MSI-H samples, upregulate MSI panel genes
msi_effect_size = {
    "immune_infiltration": 1.8,    # fold-change (PTPRC, ITGB2, LCP1, NCF2)
    "interferon_response": 2.2,    # fold-change (GBP1, GBP4, IRF1, IFI35, WARS)
    "antigen_presentation": 1.6,   # fold-change (TAP1, TAPBP, LAG3)
    "mismatch_repair_adjacent": 1.4,  # fold-change (CIITA, TYMP)
}

for sample_idx in msi_h_indices:
    for pathway, genes in KNOWN_MSI_PATHWAY_MARKERS.items():
        for gene in genes:
            if gene in gene_columns:
                col_idx = gene_columns.index(gene)
                fold = msi_effect_size[pathway]
                noise = rng.normal(0, 0.15)  # biological variability
                base[sample_idx, col_idx] *= (fold + noise)
```

This produces ANOVA p-values < 0.05 for pathway genes while leaving non-MSI genes as noise — exactly what the feature selection module should recover.

> **Note:** The pathway names used here (e.g., `"immune_infiltration"`, `"interferon_response"`) should align with a `PATHWAY_MECHANISMS` constant to be added to `core/constants.py`. This constant does not yet exist and would need to be created alongside this module.

**Key parameter: `msi_prevalence`** — defaults to 0.15 (matching the real CPTAC cohort's ~15% MSI-H rate). This preserves the class imbalance the Label-Weighted k-NN was designed to handle.

### 1.2 Gender Signal

Y-chromosome genes (DDX3Y, EIF1AY, KDM5D, RPS4Y1, USP9Y, UTY, ZFY) must show strong male expression and near-zero female expression. X-inactivation escape genes (KDM5C, XIST) show the inverse.

```python
for sample_idx, gender in enumerate(gender_labels):
    for gene in Y_CHROMOSOME_GENES:
        if gene in gene_columns:
            col_idx = gene_columns.index(gene)
            if gender == "Male":
                base[sample_idx, col_idx] = rng.lognormal(4.0, 0.5)
            else:
                base[sample_idx, col_idx] = 0.0  # will become NaN in MNAR step
```

This ensures gender classification is trivially separable, matching real-world Y-chromosome expression patterns.

### 1.3 Gene-Gene Correlation Structure

Real expression data has pathway-level correlation — immune genes co-vary, housekeeping genes are stable. Without this, the NMF imputation has no latent structure to discover.

**Strategy — Block-correlated noise via Cholesky decomposition:**

```python
# Define correlation blocks
pathway_blocks = {
    "immune": ["PTPRC", "ITGB2", "LCP1", "NCF2", "PTPN6"],
    "interferon": ["GBP1", "GBP4", "IRF1", "IFI35", "WARS"],
    "housekeeping": ["GAPDH", "ACTB", "TUBA1A"],
}

# For each block, generate correlated noise (rho ~0.5-0.7)
for block_name, block_genes in pathway_blocks.items():
    indices = [gene_columns.index(g) for g in block_genes if g in gene_columns]
    n = len(indices)
    rho = 0.6
    cov = np.full((n, n), rho) + np.eye(n) * (1 - rho)
    L = np.linalg.cholesky(cov)
    for sample_idx in range(n_samples):
        z = rng.standard_normal(n)
        correlated = L @ z
        for i, col_idx in enumerate(indices):
            base[sample_idx, col_idx] *= np.exp(correlated[i] * 0.3)
```

This gives NMF real latent factors to discover (k ≈ 3–5 should capture immune, interferon, housekeeping blocks), validating the hyperparameter sweep in Stage 1 of the pipeline.

---

## Layer 2: Cross-Omics Concordance

The cross-omics matcher relies on Spearman correlation between proteomics and RNA-Seq for the same sample being higher than cross-sample correlations. This requires shared biological signal between the two modalities.

**Strategy — Shared latent factors with modality-specific noise:**

```python
# Shared latent profile per sample (represents true biological state)
n_latent = 5
sample_profiles = rng.standard_normal((n_samples, n_latent))

# Proteomics = f(shared_profile) + proteomics_noise
# RNA-Seq    = g(shared_profile) + rnaseq_noise

# For overlapping genes (present in both modalities):
for gene in overlapping_genes:
    pro_idx = proteomics_genes.index(gene)
    rna_idx = rnaseq_genes.index(gene)
    
    # Gene-specific loading on latent factors
    loading = rng.standard_normal(n_latent) * 0.5
    
    for sample_idx in range(n_samples):
        shared_signal = sample_profiles[sample_idx] @ loading
        proteomics[sample_idx, pro_idx] *= np.exp(shared_signal + rng.normal(0, 0.2))
        rnaseq[sample_idx, rna_idx] *= np.exp(shared_signal + rng.normal(0, 0.3))
```

The noise ratio (0.2 vs 0.3) reflects that proteomics typically has tighter technical replicability than RNA-Seq. The shared signal ensures that `CrossOmicsMatcher.compute_distance_matrix()` returns diagonal-dominant results for correctly labeled samples.

---

## Layer 3: Mislabeling Injection

The most critical layer — this creates the ground truth the entire platform detects and corrects.

### 3.1 Swap Types

Following the precisionFDA challenge design, only one modality is mislabeled per sample:

| Swap Type | Mechanism | Detection Method |
|-----------|-----------|-----------------|
| Proteomics swap | Exchange proteomics row between two samples | Cross-omics distance matrix (proteomics row doesn't match RNA-Seq row) |
| RNA-Seq swap | Exchange RNA-Seq row between two samples | Cross-omics distance matrix (RNA-Seq row doesn't match proteomics row) |
| Clinical swap | Exchange clinical labels between two samples | Classification-based (predicted phenotype ≠ annotated phenotype) |

### 3.2 Implementation

```python
def _inject_mislabels(
    self,
    clinical: pd.DataFrame,
    proteomics: pd.DataFrame,
    rnaseq: pd.DataFrame,
    mislabel_rate: float = 0.10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Swap data between sample pairs to simulate mislabeling."""
    
    n_to_swap = max(2, int(len(clinical) * mislabel_rate))
    # Ensure even number for pair-wise swaps
    n_to_swap = n_to_swap if n_to_swap % 2 == 0 else n_to_swap + 1
    
    swap_indices = self.rng.choice(len(clinical), size=n_to_swap, replace=False)
    pairs = list(zip(swap_indices[::2], swap_indices[1::2]))
    
    swap_types = ["proteomics", "rnaseq", "clinical"]
    ground_truth = {"mislabeled_samples": [], "mislabel_type": {}, "swap_pairs": []}
    
    for i, (idx_a, idx_b) in enumerate(pairs):
        swap_type = swap_types[i % len(swap_types)]
        sid_a, sid_b = clinical.iloc[idx_a]["sample_id"], clinical.iloc[idx_b]["sample_id"]
        
        if swap_type == "proteomics":
            proteomics.iloc[idx_a], proteomics.iloc[idx_b] = (
                proteomics.iloc[idx_b].copy(), proteomics.iloc[idx_a].copy()
            )
        elif swap_type == "rnaseq":
            rnaseq.iloc[idx_a], rnaseq.iloc[idx_b] = (
                rnaseq.iloc[idx_b].copy(), rnaseq.iloc[idx_a].copy()
            )
        elif swap_type == "clinical":
            for col in ["MSI_status", "gender"]:
                clinical.at[idx_a, col], clinical.at[idx_b, col] = (
                    clinical.at[idx_b, col], clinical.at[idx_a, col]
                )
        
        ground_truth["mislabeled_samples"].extend([sid_a, sid_b])
        ground_truth["mislabel_type"][sid_a] = swap_type
        ground_truth["mislabel_type"][sid_b] = swap_type
        ground_truth["swap_pairs"].append((sid_a, sid_b))
    
    return clinical, proteomics, rnaseq, ground_truth
```

**Key design choice:** Swapping between MSI-H and MSS samples (or Male and Female) produces the strongest signal. The generator preferentially selects cross-phenotype pairs for at least half the swaps, since same-phenotype swaps are harder to detect and provide a difficulty gradient.

### 3.3 Difficulty Tiers

For evaluation benchmarking, the generator supports three difficulty presets:

| Tier | Mislabel Rate | Cross-Phenotype % | Missing Rate | Purpose |
|------|--------------|-------------------|-------------|---------|
| `easy` | 5% | 100% | 5% | Smoke tests, CI pipeline |
| `medium` | 10% | 60% | 10% | Standard evaluation |
| `hard` | 15% | 40% | 20% | Stress testing, robustness claims |

---

## Layer 4: Missing Data Patterns

### 4.1 MNAR (Missing Not at Random)

Biologically determined — already handled in Layer 1:

- Y-chromosome genes set to `NaN` in all female samples
- Low-abundance proteins below detection limit: for genes with base expression in the bottom 10th percentile, apply a detection-limit censoring model

```python
# Detection limit censoring (MNAR for low-abundance proteins)
detection_threshold = np.percentile(base[base > 0], 5)
low_signal_mask = base < detection_threshold
# 70% of below-threshold values become MNAR missing
mnar_censor = low_signal_mask & (rng.random(base.shape) < 0.70)
base[mnar_censor] = np.nan
```

### 4.2 MAR (Missing at Random)

Technical dropouts that don't depend on the expression level:

```python
# Batch-structured MAR: some genes have higher dropout in a "batch"
n_batches = 3
batch_assignments = rng.choice(n_batches, size=n_samples)

for batch_id in range(n_batches):
    batch_mask = batch_assignments == batch_id
    # Each batch has a random subset of genes with elevated missingness
    n_affected_genes = int(n_genes * 0.05)
    affected = rng.choice(n_genes, size=n_affected_genes, replace=False)
    
    for gene_idx in affected:
        dropout_rate = rng.uniform(0.15, 0.40)
        for sample_idx in np.where(batch_mask)[0]:
            if rng.random() < dropout_rate:
                base[sample_idx, gene_idx] = np.nan
```

This creates the batch-correlated missingness that NMF is better at handling than naive median imputation — giving the imputation module a chance to demonstrate its value.

### 4.3 Overall Missingness Budget

Target overall rates matching the real CPTAC data:

| Modality | Target Missing % | MNAR Component | MAR Component |
|----------|-----------------|----------------|---------------|
| Proteomics | 10–15% | ~3% (Y-chr + detection limit) | ~10% (batch + random) |
| RNA-Seq | 5–10% | ~2% (Y-chr only) | ~6% (batch + random) |

---

## Layer 5: Cohort Scaling

### 5.1 Size Presets

| Preset | Samples | Pro Genes | RNA Genes | Use Case |
|--------|---------|-----------|-----------|----------|
| `unit` | 20 | 50 | 60 | Unit tests (< 1s) |
| `integration` | 80 | 200 | 250 | Integration tests, matches precisionFDA train set size |
| `benchmark` | 500 | 7,000 | 15,000 | Performance benchmarking, matches TCGA scale |
| `stress` | 2,000 | 10,000 | 20,000 | Memory/scaling stress tests |

### 5.2 Gene Name Strategy

- **First 50–60 genes**: Always drawn from `MSI_PROTEOMICS_PANEL + MSI_RNASEQ_PANEL + Y_CHROMOSOME_GENES + GENDER_PROTEOMICS_PANEL` (known signal carriers)
- **Remaining genes**: Generated as `SYNTH_GENE_{i:05d}` for unit/integration presets, or sampled from HGNC symbol lists for benchmark/stress presets (for realistic gene name distributions)

---

## Integration Points

### With `conftest.py`

Replace the current manual fixtures with generator calls:

```python
from core.synthetic import SyntheticCohortGenerator

@pytest.fixture(scope="session")
def synthetic_cohort():
    gen = SyntheticCohortGenerator(seed=42, preset="unit")
    return gen.generate_cohort()

@pytest.fixture
def sample_clinical_df(synthetic_cohort):
    return synthetic_cohort["clinical"]

@pytest.fixture
def sample_proteomics_df(synthetic_cohort):
    return synthetic_cohort["proteomics"]

@pytest.fixture
def sample_rnaseq_df(synthetic_cohort):
    return synthetic_cohort["rnaseq"]

@pytest.fixture
def ground_truth(synthetic_cohort):
    return synthetic_cohort["ground_truth"]
```

### With Evaluation Framework

The `evals/` suite gains deterministic expected answers:

| Eval | Ground Truth Source |
|------|-------------------|
| Biological Validity | MSI panel genes should rank in top-N of feature selection |
| Reproducibility | Same seed → identical cohort → identical pipeline output |
| Hallucination | Agent should not claim genes are MSI-related unless they're in the planted signal set |
| Benchmark | F1 against known mislabel ground truth |

### With MCP Tools

**Proposed addition:** The `data_loader` MCP tool would accept a `synthetic=true` parameter that triggers generation instead of file I/O, enabling Claude to run end-to-end demos without requiring real precisionFDA data files. This requires adding the parameter to the `LoadDatasetInput` schema in `mcp_server/schemas/omics.py` and the corresponding logic in `mcp_server/tools/data_loader.py`.

### With Temporal Workflows

**Proposed addition:** The `BiomarkerDiscoveryWorkflow` would include a `generate_synthetic_data` activity as an optional first step, making the entire pipeline self-contained for demonstrations and CI. This activity does not currently exist in `workflows/activities/`.

---

## Implementation Sequence

| Step | Task | Estimated Time |
|------|------|---------------|
| 1 | Create `core/synthetic.py` with `SyntheticCohortGenerator` class | 3 hours |
| 2 | Implement Layer 1 (MSI + gender signal injection with pathway correlations) | 2 hours |
| 3 | Implement Layer 2 (cross-omics shared latent factors) | 1.5 hours |
| 4 | Implement Layer 3 (mislabel injection with difficulty tiers) | 1.5 hours |
| 5 | Implement Layer 4 (MNAR + MAR missingness with batch structure) | 1 hour |
| 6 | Add presets and gene scaling logic | 1 hour |
| 7 | Refactor `conftest.py` to use generator | 30 min |
| 8 | Validation: run full pipeline on `integration` preset, verify F1 > 0.8 | 1 hour |
| 9 | Add `synthetic` parameter to `data_loader` MCP tool | 30 min |

**Total: ~12 hours of focused implementation.**

---

## Validation Criteria

The synthetic data is "good enough" when these conditions hold:

1. **Feature selection recovers planted signal** — At least 80% of MSI pathway genes appear in the top-30 selected features across any method
2. **Cross-omics matcher detects swaps** — Distance matrix diagonal dominance breaks exactly at mislabeled samples
3. **Ensemble classifier F1 ≥ 0.85** — On the `medium` difficulty tier with 10-fold CV
4. **NMF reconstruction error decreases** — Compared to median imputation on the same data, confirming the correlation structure is exploitable
5. **Gender classification is near-perfect** — Y-chromosome signal produces AUC > 0.99
6. **Deterministic reproducibility** — Same seed produces byte-identical DataFrames across runs

---

## Why Not Use Real Data Exclusively?

The precisionFDA challenge data (80 train + 80 test samples) is available and should remain the gold standard for final validation. But synthetic data solves three problems real data can't:

- **Known ground truth for mislabels** — The real test set mislabels are unknown; synthetic mislabels have verifiable answers
- **Scalability** — 80 samples is too few for stress testing, CI performance regression, or demonstrating scaling behavior in Temporal workflows
- **Eval determinism** — Real data produces stochastic eval results due to CV splits; synthetic data with a fixed seed enables exact regression testing

The recommended workflow: develop and tune on synthetic data, validate on real precisionFDA data, report both.
