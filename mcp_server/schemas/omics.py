"""Pydantic v2 Input/Output models for all 8 MCP genomics tools."""

from __future__ import annotations

from core.models import CustomBaseModel

# ---------------------------------------------------------------------------
# 1. Load Dataset
# ---------------------------------------------------------------------------


class LoadDatasetInput(CustomBaseModel):
    """Input for loading multi-omics dataset."""

    dataset: str = "train"
    modalities: list[str] = ["clinical", "proteomics", "rnaseq"]
    data_dir: str | None = None


class LoadDatasetOutput(CustomBaseModel):
    """Output from loading multi-omics dataset."""

    samples: int
    features: dict[str, int]
    msi_distribution: dict[str, int]
    gender_distribution: dict[str, int]
    missing_data_summary: dict[str, float]


# ---------------------------------------------------------------------------
# 2. Impute Missing
# ---------------------------------------------------------------------------


class ImputeMissingInput(CustomBaseModel):
    """Input for missing value imputation."""

    dataset: str = "train"
    modality: str = "proteomics"
    strategy: str = "nmf"
    classify_missingness: bool = True


class ImputeMissingOutput(CustomBaseModel):
    """Output from missing value imputation."""

    genes_before: int
    genes_imputed_mar: int
    genes_assigned_mnar_zero: int
    nmf_reconstruction_error: float
    features_recovered: int
    comparison: dict[str, float]


# ---------------------------------------------------------------------------
# 3. Check Availability
# ---------------------------------------------------------------------------


class CheckAvailabilityInput(CustomBaseModel):
    """Input for gene availability check."""

    genes: list[str] | None = None
    threshold: float = 0.9
    dataset: str = "train"
    use_imputed: bool = True


class CheckAvailabilityOutput(CustomBaseModel):
    """Output from gene availability check."""

    available: list[str]
    filtered: list[str]
    availability_scores: dict[str, float]
    imputation_impact: dict[str, float]


# ---------------------------------------------------------------------------
# 4. Select Biomarkers
# ---------------------------------------------------------------------------


class SelectBiomarkersInput(CustomBaseModel):
    """Input for biomarker selection."""

    target: str = "msi"
    modality: str = "proteomics"
    methods: list[str] | str = "all"
    integration: str = "union_weighted"
    n_top: int = 30
    p_value_correction: str = "both"


class SelectBiomarkersOutput(CustomBaseModel):
    """Output from biomarker selection."""

    biomarkers: list[dict]
    method_agreement: dict[str, list[str]]
    comparison_to_original: dict[str, float]


# ---------------------------------------------------------------------------
# 5. Run Classification
# ---------------------------------------------------------------------------


class RunClassificationInput(CustomBaseModel):
    """Input for ensemble classification."""

    features: list[str] | str = "auto"
    target: str = "mismatch"
    classifiers: list[str] | str = "ensemble"
    phenotype_strategy: str = "both"
    meta_learner: str = "logistic_regression"
    test_size: float = 0.3
    cv_folds: int = 10


class RunClassificationOutput(CustomBaseModel):
    """Output from ensemble classification."""

    ensemble_f1: float
    per_classifier_f1: dict[str, float]
    best_strategy: str
    strategy_comparison: dict[str, float]
    feature_importances: list[dict]
    comparison_to_baseline: dict[str, float]


# ---------------------------------------------------------------------------
# 6. Match Cross-Omics
# ---------------------------------------------------------------------------


class MatchCrossOmicsInput(CustomBaseModel):
    """Input for cross-omics matching."""

    dataset: str = "train"
    distance_method: str = "both"
    n_iterations: int = 100
    gene_sampling_fraction: float = 0.8


class MatchCrossOmicsOutput(CustomBaseModel):
    """Output from cross-omics matching."""

    distance_matrix_info: dict
    identified_mismatches: list[dict]
    iteration_agreement: float


# ---------------------------------------------------------------------------
# 7. Evaluate Model
# ---------------------------------------------------------------------------


class EvaluateModelInput(CustomBaseModel):
    """Input for model evaluation."""

    model_id: str = "ensemble"
    test_data: str = "holdout"
    compare_to_baseline: bool = True


class EvaluateModelOutput(CustomBaseModel):
    """Output from model evaluation."""

    f1_score: float
    precision: float
    recall: float
    confusion_matrix: list
    roc_auc: float
    baseline_comparison: dict[str, float]


# ---------------------------------------------------------------------------
# 8. Explain Features
# ---------------------------------------------------------------------------


class ExplainFeaturesInput(CustomBaseModel):
    """Input for feature explanation."""

    genes: list[str]
    context: str = "msi_classification"
    include_provenance: bool = True


class ExplainFeaturesOutput(CustomBaseModel):
    """Output from feature explanation."""

    explanations: list[dict]


# ---------------------------------------------------------------------------
# 9. Explain Features (Local SLM)
# ---------------------------------------------------------------------------


class ExplainFeaturesLocalInput(CustomBaseModel):
    """Input for local SLM-based feature explanation."""

    genes: list[str]
    context: str = "msi_classification"
    target: str = "msi"
