"""Tests for mcp_server.tools.explainer."""

from __future__ import annotations

import pytest

from mcp_server.schemas.omics import ExplainFeaturesInput, ExplainFeaturesOutput


@pytest.mark.asyncio
async def test_explain_known_marker():
    """Test explanation for a known MSI marker."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=["TAP1"])
    result = await run_tool(inp)

    assert isinstance(result, ExplainFeaturesOutput)
    assert len(result.explanations) == 1
    assert result.explanations[0]["gene"] == "TAP1"
    assert result.explanations[0]["known_msi_marker"] is True


@pytest.mark.asyncio
async def test_explain_novel_gene():
    """Test explanation for a gene not in known pathways."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=["BRCA1"])
    result = await run_tool(inp)

    assert len(result.explanations) == 1
    assert result.explanations[0]["known_msi_marker"] is False


@pytest.mark.asyncio
async def test_explain_multiple_genes():
    """Test explanation for multiple genes."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=["TAP1", "GBP1", "BRCA1", "PTPRC"])
    result = await run_tool(inp)

    assert len(result.explanations) == 4
    known_count = sum(1 for e in result.explanations if e["known_msi_marker"])
    assert known_count == 3  # TAP1, GBP1, PTPRC are known


@pytest.mark.asyncio
async def test_explain_pathways():
    """Test that pathway membership is correct."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=["TAP1"])
    result = await run_tool(inp)

    pathways = result.explanations[0]["pathways"]
    assert "antigen_presentation" in pathways


@pytest.mark.asyncio
async def test_explain_provenance_included():
    """Test that provenance is included when requested."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=["TAP1"], include_provenance=True)
    result = await run_tool(inp)

    assert "provenance" in result.explanations[0]
    assert result.explanations[0]["provenance"]["source"] == "KNOWN_MSI_PATHWAY_MARKERS"


@pytest.mark.asyncio
async def test_explain_empty_genes():
    """Test with empty gene list."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=[])
    result = await run_tool(inp)

    assert result.explanations == []


@pytest.mark.asyncio
async def test_explain_serialization():
    """Test output serialization."""
    from mcp_server.tools.explainer import run_tool

    inp = ExplainFeaturesInput(genes=["GBP1", "IRF1"])
    result = await run_tool(inp)

    dumped = result.model_dump()
    assert "explanations" in dumped
    assert len(dumped["explanations"]) == 2
