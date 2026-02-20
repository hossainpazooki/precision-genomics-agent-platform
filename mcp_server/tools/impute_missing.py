"""MCP tool: Impute missing values in omics data."""

from __future__ import annotations

import numpy as np

from core.data_loader import OmicsDataLoader
from core.imputation import OmicsImputer
from mcp_server.schemas.omics import ImputeMissingInput, ImputeMissingOutput


async def run_tool(
    input_data: ImputeMissingInput,
    expression_matrix=None,
    clinical_df=None,
) -> ImputeMissingOutput:
    """Run imputation on the loaded omics data.

    Delegates to ``core.imputation.OmicsImputer.impute()``.

    Parameters
    ----------
    input_data : ImputeMissingInput
        Tool input schema.
    expression_matrix : pd.DataFrame, optional
        Pre-loaded expression matrix (samples x genes). When *None* the tool
        loads from disk via OmicsDataLoader.
    clinical_df : pd.DataFrame, optional
        Pre-loaded clinical data. When *None* the tool loads from disk.
    """
    if expression_matrix is None or clinical_df is None:
        loader = OmicsDataLoader()
        if clinical_df is None:
            clinical_df = loader.load_clinical(input_data.dataset)
        if expression_matrix is None:
            if input_data.modality == "rnaseq":
                expression_matrix = loader.load_rnaseq(input_data.dataset)
            else:
                expression_matrix = loader.load_proteomics(input_data.dataset)

    genes_before = expression_matrix.shape[1]

    imputer = OmicsImputer()
    imputed_matrix, stats = imputer.impute(expression_matrix, clinical_df)

    # Reconstruction error: mean squared diff on non-NaN positions
    original_vals = expression_matrix.values.copy()
    imputed_vals = imputed_matrix.values.copy()
    observed_mask = ~np.isnan(original_vals)
    if observed_mask.sum() > 0:
        recon_error = float(
            np.mean((original_vals[observed_mask] - imputed_vals[observed_mask]) ** 2)
        )
    else:
        recon_error = 0.0

    return ImputeMissingOutput(
        genes_before=genes_before,
        genes_imputed_mar=stats.get("n_mar", 0),
        genes_assigned_mnar_zero=stats.get("n_mnar", 0),
        nmf_reconstruction_error=round(recon_error, 6),
        features_recovered=genes_before - int(imputed_matrix.isna().any().sum()),
        comparison={
            "total_missing_before": float(stats.get("total_missing", 0)),
            "remaining_nan": float(stats.get("remaining_nan", 0)),
            "pct_mnar": float(stats.get("pct_mnar", 0.0)),
            "pct_mar": float(stats.get("pct_mar", 0.0)),
        },
    )
