"""Multi-omics data loading and preprocessing.

Handles TSV ingestion for precisionFDA challenge data: clinical, proteomics,
and RNA-Seq modalities.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import get_settings


class OmicsDataLoader:
    """Load and merge multi-omics datasets from TSV files."""

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(get_settings().raw_data_dir)

    def load_clinical(self, dataset: str = "train") -> pd.DataFrame:
        """Load clinical annotations (sample_id, MSI_status, gender, etc.)."""
        path = self.data_dir / f"{dataset}_cli.tsv"
        df = pd.read_csv(path, sep="\t")
        return df

    def load_proteomics(self, dataset: str = "train") -> pd.DataFrame:
        """Load proteomics expression matrix (genes as rows in TSV, transposed to samples×genes)."""
        path = self.data_dir / f"{dataset}_pro.tsv"
        df = pd.read_csv(path, sep="\t", index_col=0)
        return df.T

    def load_rnaseq(self, dataset: str = "train") -> pd.DataFrame:
        """Load RNA-Seq expression matrix (transposed to samples×genes)."""
        path = self.data_dir / f"{dataset}_rna.tsv"
        df = pd.read_csv(path, sep="\t", index_col=0)
        return df.T

    def merge_clinical_molecular(
        self, clinical_df: pd.DataFrame, molecular_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge clinical and molecular data on sample index."""
        clinical = clinical_df.copy()
        if "sample_id" in clinical.columns:
            clinical = clinical.set_index("sample_id")
        merged = molecular_df.join(clinical, how="inner")
        return merged

    def get_dataset_summary(self, dataset: str = "train") -> dict:
        """Return summary statistics for a dataset."""
        clinical = self.load_clinical(dataset)

        summary: dict = {
            "dataset": dataset,
            "n_samples": len(clinical),
        }

        # MSI distribution
        if "MSI_status" in clinical.columns:
            summary["msi_distribution"] = clinical["MSI_status"].value_counts().to_dict()

        # Gender distribution
        if "gender" in clinical.columns:
            summary["gender_distribution"] = clinical["gender"].value_counts().to_dict()

        # Feature counts per modality
        try:
            pro = self.load_proteomics(dataset)
            summary["n_proteomics_features"] = pro.shape[1]
            summary["pct_missing_proteomics"] = round(
                pro.isna().sum().sum() / (pro.shape[0] * pro.shape[1]) * 100, 2
            )
        except FileNotFoundError:
            summary["n_proteomics_features"] = 0

        try:
            rna = self.load_rnaseq(dataset)
            summary["n_rnaseq_features"] = rna.shape[1]
            summary["pct_missing_rnaseq"] = round(
                rna.isna().sum().sum() / (rna.shape[0] * rna.shape[1]) * 100, 2
            )
        except FileNotFoundError:
            summary["n_rnaseq_features"] = 0

        return summary
