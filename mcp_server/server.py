"""MCP server entrypoint for the Precision Genomics Agent Platform.

Exposes 8 genomics tools over the Model Context Protocol (MCP) via stdio
transport.  Each tool validates its input with a Pydantic schema, delegates
to the corresponding ``mcp_server/tools/*.py`` function, and returns a
structured output schema.
"""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    _MCP_AVAILABLE = True
except ImportError:
    Server = None  # type: ignore[assignment,misc]
    _MCP_AVAILABLE = False

from mcp_server.schemas.omics import (  # noqa: E402
    CheckAvailabilityInput,
    EvaluateModelInput,
    ExplainFeaturesInput,
    ImputeMissingInput,
    LoadDatasetInput,
    MatchCrossOmicsInput,
    RunClassificationInput,
    SelectBiomarkersInput,
)

# ---------------------------------------------------------------------------
# Tool registry: name -> (schema_class, module_path, description)
# ---------------------------------------------------------------------------

_TOOL_REGISTRY: dict[str, tuple[type, str, str]] = {
    "load_dataset": (
        LoadDatasetInput,
        "mcp_server.tools.data_loader",
        "Load a multi-omics dataset (clinical, proteomics, RNA-Seq) and "
        "return summary statistics including sample count, feature counts, "
        "MSI/gender distributions, and missing-data rates.",
    ),
    "impute_missing": (
        ImputeMissingInput,
        "mcp_server.tools.impute_missing",
        "Classify missing values as MNAR or MAR and impute them using NMF. "
        "Returns imputation statistics and reconstruction error.",
    ),
    "check_availability": (
        CheckAvailabilityInput,
        "mcp_server.tools.availability_check",
        "Check gene availability (fraction of non-missing samples) and filter genes by a configurable threshold.",
    ),
    "select_biomarkers": (
        SelectBiomarkersInput,
        "mcp_server.tools.biomarker_selector",
        "Run multi-strategy biomarker selection (ANOVA, LASSO, NSC, RF) "
        "with ensemble integration to identify top discriminating genes.",
    ),
    "run_classification": (
        RunClassificationInput,
        "mcp_server.tools.classifier",
        "Train an ensemble mismatch classifier using the selected "
        "biomarkers and evaluate performance with cross-validation.",
    ),
    "match_cross_omics": (
        MatchCrossOmicsInput,
        "mcp_server.tools.match_cross_omics",
        "Build a cross-omics distance matrix between proteomics and "
        "RNA-Seq profiles and identify sample-level mismatches.",
    ),
    "evaluate_model": (
        EvaluateModelInput,
        "mcp_server.tools.evaluator",
        "Evaluate a trained classifier on holdout data, reporting F1, "
        "precision, recall, confusion matrix, and ROC-AUC.",
    ),
    "explain_features": (
        ExplainFeaturesInput,
        "mcp_server.tools.explainer",
        "Generate biological explanations for selected biomarker genes "
        "using known MSI pathway markers and optional LLM enrichment.",
    ),
}


def create_server() -> Server:
    """Create and configure the MCP server with all genomics tools.

    Returns
    -------
    Server
        A configured MCP ``Server`` instance ready to run.
    """
    if not _MCP_AVAILABLE:
        raise ImportError("The 'mcp' package is required to run the MCP server. Install it with: pip install mcp")

    server = Server("genomics-omics-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools: list[Tool] = []
        for name, (schema_cls, _, description) in _TOOL_REGISTRY.items():
            tools.append(
                Tool(
                    name=name,
                    description=description,
                    inputSchema=schema_cls.model_json_schema(),
                )
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name not in _TOOL_REGISTRY:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"}),
                )
            ]

        schema_cls, module_path, _ = _TOOL_REGISTRY[name]

        try:
            input_data = schema_cls.model_validate(arguments)

            import importlib

            module = importlib.import_module(module_path)
            result = await module.run_tool(input_data)

            return [
                TextContent(
                    type="text",
                    text=result.model_dump_json(indent=2),
                )
            ]
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": str(exc),
                            "tool": name,
                            "type": type(exc).__name__,
                        }
                    ),
                )
            ]

    return server


async def main() -> None:
    """Run the MCP server over stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
