"""MCP tool: Select biomarker features using multi-strategy ensemble."""

from __future__ import annotations

from core.constants import MSI_PROTEOMICS_PANEL, MSI_RNASEQ_PANEL
from core.feature_selection import MultiStrategySelector
from mcp_server.schemas.omics import SelectBiomarkersInput, SelectBiomarkersOutput


async def run_tool(
    input_data: SelectBiomarkersInput,
    X=None,
    y=None,
) -> SelectBiomarkersOutput:
    """Run multi-strategy biomarker selection.

    Delegates to ``core.feature_selection.MultiStrategySelector.ensemble_select()``.

    Parameters
    ----------
    input_data : SelectBiomarkersInput
        Tool input schema.
    X : pd.DataFrame, optional
        Feature matrix (samples x genes).
    y : pd.Series, optional
        Target labels.
    """
    selector = MultiStrategySelector()
    panel = selector.ensemble_select(
        X=X,
        y=y,
        target=input_data.target,
        modality=input_data.modality,
        strategy=input_data.integration,
        n_top=input_data.n_top,
    )

    # Build biomarkers list from panel features
    biomarkers = [
        {
            "gene": f.name,
            "score": f.score,
            "rank": f.rank,
            "method": f.method,
            "p_value": f.p_value,
        }
        for f in panel.features
    ]

    # Compare to original panels
    original_panel = MSI_PROTEOMICS_PANEL if input_data.modality == "proteomics" else MSI_RNASEQ_PANEL
    selected_genes = {f.name for f in panel.features}
    original_set = set(original_panel)

    overlap = selected_genes & original_set
    comparison: dict[str, float] = {
        "overlap_count": float(len(overlap)),
        "overlap_fraction": round(len(overlap) / max(len(original_set), 1), 4),
        "novel_count": float(len(selected_genes - original_set)),
    }

    return SelectBiomarkersOutput(
        biomarkers=biomarkers,
        method_agreement=panel.method_agreement,
        comparison_to_original=comparison,
    )
