"""MCP tool: Explain features using local SLM or Vertex AI endpoint."""

from __future__ import annotations

import logging

from mcp_server.schemas.omics import ExplainFeaturesLocalInput, ExplainFeaturesOutput

logger = logging.getLogger(__name__)


async def run_tool(input_data: ExplainFeaturesLocalInput) -> ExplainFeaturesOutput:
    """Use get_explainer() factory, falls back to existing explainer if SLM unavailable."""
    explanations: list[dict] = []

    try:
        from training.explainer import get_explainer

        explainer = get_explainer()

        for gene in input_data.genes:
            result = await explainer.classify_gene(gene, input_data.target)
            explanations.append({
                "gene": gene,
                "context": input_data.context,
                "source": "slm",
                **result,
            })

    except (ValueError, ImportError) as exc:
        logger.warning("SLM explainer unavailable (%s), falling back to static explainer", exc)

        # Fall back to the existing explainer tool
        from mcp_server.schemas.omics import ExplainFeaturesInput
        from mcp_server.tools.explainer import run_tool as fallback_run_tool

        fallback_input = ExplainFeaturesInput(
            genes=input_data.genes,
            context=input_data.context,
            include_provenance=True,
        )
        fallback_result = await fallback_run_tool(fallback_input)
        return fallback_result

    return ExplainFeaturesOutput(explanations=explanations)
