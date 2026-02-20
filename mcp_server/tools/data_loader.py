"""MCP tool: Load multi-omics dataset."""

from __future__ import annotations

from core.data_loader import OmicsDataLoader
from mcp_server.schemas.omics import LoadDatasetInput, LoadDatasetOutput


async def run_tool(input_data: LoadDatasetInput) -> LoadDatasetOutput:
    """Load dataset and return summary statistics.

    Delegates to ``core.data_loader.OmicsDataLoader`` for TSV ingestion.
    """
    loader = OmicsDataLoader(data_dir=input_data.data_dir)

    feature_counts: dict[str, int] = {}
    missing_summary: dict[str, float] = {}
    n_samples = 0
    msi_dist: dict[str, int] = {}
    gender_dist: dict[str, int] = {}

    if "clinical" in input_data.modalities:
        try:
            clinical = loader.load_clinical(input_data.dataset)
            n_samples = len(clinical)
            if "MSI_status" in clinical.columns:
                msi_dist = clinical["MSI_status"].value_counts().to_dict()
            if "gender" in clinical.columns:
                gender_dist = clinical["gender"].value_counts().to_dict()
        except FileNotFoundError:
            pass

    if "proteomics" in input_data.modalities:
        try:
            pro = loader.load_proteomics(input_data.dataset)
            feature_counts["proteomics"] = pro.shape[1]
            total_cells = pro.shape[0] * pro.shape[1]
            missing_summary["proteomics"] = round(
                pro.isna().sum().sum() / total_cells * 100, 2
            ) if total_cells > 0 else 0.0
            if n_samples == 0:
                n_samples = pro.shape[0]
        except FileNotFoundError:
            pass

    if "rnaseq" in input_data.modalities:
        try:
            rna = loader.load_rnaseq(input_data.dataset)
            feature_counts["rnaseq"] = rna.shape[1]
            total_cells = rna.shape[0] * rna.shape[1]
            missing_summary["rnaseq"] = round(
                rna.isna().sum().sum() / total_cells * 100, 2
            ) if total_cells > 0 else 0.0
            if n_samples == 0:
                n_samples = rna.shape[0]
        except FileNotFoundError:
            pass

    return LoadDatasetOutput(
        samples=n_samples,
        features=feature_counts,
        msi_distribution=msi_dist,
        gender_distribution=gender_dist,
        missing_data_summary=missing_summary,
    )
