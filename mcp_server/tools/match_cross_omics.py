"""MCP tool: Cross-omics sample matching and mismatch detection."""

from __future__ import annotations

import numpy as np

from core.cross_omics_matcher import CrossOmicsMatcher
from mcp_server.schemas.omics import MatchCrossOmicsInput, MatchCrossOmicsOutput


async def run_tool(
    input_data: MatchCrossOmicsInput,
    proteomics_df=None,
    rnaseq_df=None,
    gene_set=None,
) -> MatchCrossOmicsOutput:
    """Match samples across omics modalities to detect mismatches.

    Delegates to ``core.cross_omics_matcher.CrossOmicsMatcher``.

    Parameters
    ----------
    input_data : MatchCrossOmicsInput
        Tool input schema.
    proteomics_df, rnaseq_df : pd.DataFrame, optional
        Expression matrices for the two modalities.
    gene_set : list[str], optional
        Shared genes to use for distance computation.
    """
    matcher = CrossOmicsMatcher()

    # Compute gene correlations
    matcher.compute_gene_correlations(proteomics_df, rnaseq_df)

    # Determine shared gene set if not provided
    if gene_set is None and proteomics_df is not None and rnaseq_df is not None:
        gene_set = sorted(
            set(proteomics_df.columns) & set(rnaseq_df.columns)
        )

    # Build distance matrix
    distance_matrix = matcher.build_distance_matrix(
        proteomics_df,
        rnaseq_df,
        gene_set,
        method=input_data.distance_method if input_data.distance_method != "both" else "expression_rank",
    )

    # Identify mismatches
    mismatches = matcher.identify_mismatches(
        distance_matrix,
        n_iterations=input_data.n_iterations,
        sampling_fraction=input_data.gene_sampling_fraction,
    )

    # Summarize distance matrix
    dm_info: dict = {
        "shape": list(distance_matrix.shape) if hasattr(distance_matrix, "shape") else [],
        "mean_distance": float(np.mean(distance_matrix)) if distance_matrix is not None else 0.0,
        "method": input_data.distance_method,
    }

    # Compute iteration agreement
    if mismatches:
        agreements = [m.get("agreement", 0.0) for m in mismatches]
        iter_agreement = float(np.mean(agreements)) if agreements else 0.0
    else:
        iter_agreement = 1.0

    return MatchCrossOmicsOutput(
        distance_matrix_info=dm_info,
        identified_mismatches=mismatches,
        iteration_agreement=round(iter_agreement, 4),
    )
