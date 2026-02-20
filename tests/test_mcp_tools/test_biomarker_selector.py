"""Tests for mcp_server.tools.biomarker_selector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.schemas.omics import SelectBiomarkersInput, SelectBiomarkersOutput


class MockFeature:
    """Mock feature object returned by MultiStrategySelector."""

    def __init__(self, name, score, rank, method, p_value):
        self.name = name
        self.score = score
        self.rank = rank
        self.method = method
        self.p_value = p_value


class MockPanel:
    """Mock panel returned by ensemble_select."""

    def __init__(self, features, method_agreement):
        self.features = features
        self.method_agreement = method_agreement


@pytest.fixture
def mock_selector():
    """Create a mock MultiStrategySelector."""
    selector = MagicMock()
    features = [
        MockFeature("TAP1", 0.95, 1, "anova", 0.001),
        MockFeature("GBP1", 0.90, 2, "lasso", 0.002),
        MockFeature("PTPRC", 0.85, 3, "random_forest", 0.005),
    ]
    panel = MockPanel(
        features=features,
        method_agreement={"anova": ["TAP1", "GBP1"], "lasso": ["TAP1"]},
    )
    selector.ensemble_select.return_value = panel
    return selector


@pytest.mark.asyncio
async def test_select_biomarkers_default(mock_selector):
    """Test biomarker selection with defaults."""
    with patch("core.feature_selection.MultiStrategySelector", return_value=mock_selector):
        from mcp_server.tools.biomarker_selector import run_tool

        inp = SelectBiomarkersInput()
        result = await run_tool(inp)

    assert isinstance(result, SelectBiomarkersOutput)
    assert len(result.biomarkers) == 3


@pytest.mark.asyncio
async def test_select_biomarkers_gene_names(mock_selector):
    """Test that biomarker gene names are correct."""
    with patch("core.feature_selection.MultiStrategySelector", return_value=mock_selector):
        from mcp_server.tools.biomarker_selector import run_tool

        inp = SelectBiomarkersInput()
        result = await run_tool(inp)

    genes = [b["gene"] for b in result.biomarkers]
    assert "TAP1" in genes
    assert "GBP1" in genes


@pytest.mark.asyncio
async def test_select_biomarkers_method_agreement(mock_selector):
    """Test method agreement reporting."""
    with patch("core.feature_selection.MultiStrategySelector", return_value=mock_selector):
        from mcp_server.tools.biomarker_selector import run_tool

        inp = SelectBiomarkersInput()
        result = await run_tool(inp)

    assert "anova" in result.method_agreement


@pytest.mark.asyncio
async def test_select_biomarkers_comparison(mock_selector):
    """Test comparison to original panels."""
    with patch("core.feature_selection.MultiStrategySelector", return_value=mock_selector):
        from mcp_server.tools.biomarker_selector import run_tool

        inp = SelectBiomarkersInput(modality="proteomics")
        result = await run_tool(inp)

    assert "overlap_count" in result.comparison_to_original
    assert "overlap_fraction" in result.comparison_to_original


@pytest.mark.asyncio
async def test_select_biomarkers_rnaseq(mock_selector):
    """Test biomarker selection for RNA-Seq modality."""
    with patch("core.feature_selection.MultiStrategySelector", return_value=mock_selector):
        from mcp_server.tools.biomarker_selector import run_tool

        inp = SelectBiomarkersInput(modality="rnaseq")
        result = await run_tool(inp)

    assert isinstance(result, SelectBiomarkersOutput)
    assert "novel_count" in result.comparison_to_original


@pytest.mark.asyncio
async def test_select_biomarkers_serialization(mock_selector):
    """Test that output serializes correctly."""
    with patch("core.feature_selection.MultiStrategySelector", return_value=mock_selector):
        from mcp_server.tools.biomarker_selector import run_tool

        inp = SelectBiomarkersInput()
        result = await run_tool(inp)

    dumped = result.model_dump()
    assert isinstance(dumped, dict)
    assert "biomarkers" in dumped
    assert "method_agreement" in dumped
    assert "comparison_to_original" in dumped
