"""MCP tool: Check gene availability after imputation."""

from __future__ import annotations

from core.availability import AvailabilityFilter
from core.data_loader import OmicsDataLoader
from mcp_server.schemas.omics import CheckAvailabilityInput, CheckAvailabilityOutput


async def run_tool(
    input_data: CheckAvailabilityInput,
    expression_matrix=None,
    imputed_matrix=None,
) -> CheckAvailabilityOutput:
    """Filter genes by availability threshold.

    Delegates to ``core.availability.AvailabilityFilter``.

    Parameters
    ----------
    input_data : CheckAvailabilityInput
        Tool input schema.
    expression_matrix : pd.DataFrame, optional
        Original expression matrix (for imputation impact comparison).
    imputed_matrix : pd.DataFrame, optional
        Imputed expression matrix to evaluate. Falls back to *expression_matrix*.
    """
    filt = AvailabilityFilter()

    matrix = imputed_matrix if imputed_matrix is not None else expression_matrix

    if matrix is None:
        loader = OmicsDataLoader()
        matrix = loader.load_proteomics(input_data.dataset)

    # Optionally subset to requested genes
    if input_data.genes is not None:
        valid_genes = [g for g in input_data.genes if g in matrix.columns]
        matrix = matrix[valid_genes]

    available, filtered, scores = filt.filter_genes(
        matrix,
        threshold=input_data.threshold,
        use_imputed=input_data.use_imputed,
    )

    # Compute imputation impact if we have both original and imputed
    impact: dict[str, float] = {}
    if expression_matrix is not None and imputed_matrix is not None:
        comparison = filt.compare_pre_post_imputation(expression_matrix, imputed_matrix, input_data.threshold)
        impact = {
            "genes_rescued": float(len(comparison.get("genes_rescued", []))),
            "before_count": float(comparison.get("before_count", 0)),
            "after_count": float(comparison.get("after_count", 0)),
        }

    return CheckAvailabilityOutput(
        available=available,
        filtered=filtered,
        availability_scores=scores,
        imputation_impact=impact,
    )
