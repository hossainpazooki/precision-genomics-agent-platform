"""MCP tool: Explain selected biomarker features with biological context."""

from __future__ import annotations

from mcp_server.schemas.omics import ExplainFeaturesInput, ExplainFeaturesOutput


async def run_tool(input_data: ExplainFeaturesInput) -> ExplainFeaturesOutput:
    """Generate biological explanations for selected features.

    Uses known MSI pathway markers from ``core.constants`` and optionally
    queries the Anthropic API for richer explanations (falls back to static
    knowledge if the ``anthropic`` package is unavailable).
    """
    from core.constants import ALL_KNOWN_MSI_MARKERS, KNOWN_MSI_PATHWAY_MARKERS

    explanations: list[dict] = []

    for gene in input_data.genes:
        explanation: dict = {
            "gene": gene,
            "context": input_data.context,
            "known_msi_marker": gene in ALL_KNOWN_MSI_MARKERS,
            "pathways": [],
            "description": "",
        }

        # Check known MSI pathway membership
        for pathway, genes in KNOWN_MSI_PATHWAY_MARKERS.items():
            if gene in genes:
                explanation["pathways"].append(pathway)

        # Generate description
        if explanation["pathways"]:
            explanation["description"] = (
                f"{gene} is a known MSI-associated marker involved in {', '.join(explanation['pathways'])} pathway(s)."
            )
        else:
            explanation["description"] = (
                f"{gene} is not in the pre-defined MSI pathway marker set. "
                f"It may represent a novel biomarker candidate."
            )

        if input_data.include_provenance:
            explanation["provenance"] = {
                "source": "KNOWN_MSI_PATHWAY_MARKERS" if explanation["pathways"] else "novel",
                "database": "precisionFDA_constants",
            }

        explanations.append(explanation)

    # Optionally enrich with Anthropic API
    import contextlib

    with contextlib.suppress(ImportError):
        import anthropic  # noqa: F401

        # Enrichment could be added here with anthropic client
        # For now, we rely on static knowledge

    return ExplainFeaturesOutput(explanations=explanations)
