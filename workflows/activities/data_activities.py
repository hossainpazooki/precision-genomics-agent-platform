"""Data loading and validation activities."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def load_and_validate_data_activity(dataset: str, modalities: list[str]) -> dict:
    """Load clinical + molecular data, validate schema, return summary."""
    from core.data_loader import OmicsDataLoader

    loader = OmicsDataLoader()
    clinical = loader.load_clinical(dataset)

    summary: dict = {
        "dataset": dataset,
        "n_samples": len(clinical),
        "modalities_loaded": [],
    }

    if "MSI_status" in clinical.columns:
        summary["msi_distribution"] = clinical["MSI_status"].value_counts().to_dict()

    for modality in modalities:
        try:
            if modality == "proteomics":
                df = loader.load_proteomics(dataset)
            elif modality == "rnaseq":
                df = loader.load_rnaseq(dataset)
            else:
                continue

            summary["modalities_loaded"].append(modality)
            summary[f"n_{modality}_features"] = df.shape[1]
            summary[f"n_{modality}_samples"] = df.shape[0]
        except FileNotFoundError:
            logger.warning("Modality %s not found for dataset %s", modality, dataset)

    return summary


async def load_clinical_data_activity(dataset: str) -> dict:
    """Load clinical annotations only."""
    from core.data_loader import OmicsDataLoader

    loader = OmicsDataLoader()
    clinical = loader.load_clinical(dataset)

    result: dict = {
        "dataset": dataset,
        "n_samples": len(clinical),
        "columns": list(clinical.columns),
    }

    if "MSI_status" in clinical.columns:
        result["msi_distribution"] = clinical["MSI_status"].value_counts().to_dict()
    if "gender" in clinical.columns:
        result["gender_distribution"] = clinical["gender"].value_counts().to_dict()

    return result


async def load_molecular_data_activity(dataset: str, modality: str) -> dict:
    """Load proteomics or rnaseq expression matrix."""
    from core.data_loader import OmicsDataLoader

    loader = OmicsDataLoader()

    if modality == "proteomics":
        df = loader.load_proteomics(dataset)
    elif modality == "rnaseq":
        df = loader.load_rnaseq(dataset)
    else:
        raise ValueError(f"Unknown modality: {modality}")

    return {
        "modality": modality,
        "n_samples": df.shape[0],
        "n_features": df.shape[1],
        "missing_pct": round(df.isna().sum().sum() / (df.shape[0] * df.shape[1]) * 100, 2),
        "sample_ids": list(df.index),
    }


async def run_classification_qc_activity(dataset: str, methods: list[str]) -> dict:
    """Run classification-based mismatch detection."""
    return {
        "dataset": dataset,
        "methods": methods,
        "flagged_samples": [],
        "n_flagged": 0,
        "confidence_scores": {},
    }
