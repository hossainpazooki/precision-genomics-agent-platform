"""Tests for mcp_server.tools.availability_check."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from mcp_server.schemas.omics import CheckAvailabilityInput, CheckAvailabilityOutput


@pytest.fixture
def sample_matrix():
    """Expression matrix with some NaN columns."""
    rng = np.random.RandomState(42)
    data = rng.lognormal(2.0, 1.5, (20, 10))
    df = pd.DataFrame(data, columns=[f"gene_{i}" for i in range(10)])
    # Make gene_0 have 50% NaN (below threshold)
    df.iloc[:10, 0] = np.nan
    return df


@pytest.fixture
def mock_filter():
    """Create a mock AvailabilityFilter."""
    filt = MagicMock()
    filt.filter_genes.return_value = (
        ["gene_1", "gene_2", "gene_3"],  # available
        ["gene_0"],  # filtered
        {"gene_0": 0.5, "gene_1": 0.95, "gene_2": 0.98, "gene_3": 1.0},
    )
    filt.compare_pre_post_imputation.return_value = {
        "genes_rescued": ["gene_0"],
        "before_count": 3,
        "after_count": 4,
    }
    return filt


@pytest.mark.asyncio
async def test_availability_default(mock_filter, sample_matrix):
    """Test availability check with defaults."""
    with patch("mcp_server.tools.availability_check.AvailabilityFilter", return_value=mock_filter), \
         patch("mcp_server.tools.availability_check.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.availability_check import run_tool

        inp = CheckAvailabilityInput()
        result = await run_tool(inp)

    assert isinstance(result, CheckAvailabilityOutput)
    assert len(result.available) == 3
    assert len(result.filtered) == 1


@pytest.mark.asyncio
async def test_availability_scores(mock_filter, sample_matrix):
    """Test that availability scores are returned."""
    with patch("mcp_server.tools.availability_check.AvailabilityFilter", return_value=mock_filter), \
         patch("mcp_server.tools.availability_check.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.availability_check import run_tool

        inp = CheckAvailabilityInput()
        result = await run_tool(inp)

    assert "gene_0" in result.availability_scores
    assert result.availability_scores["gene_0"] == 0.5


@pytest.mark.asyncio
async def test_availability_custom_threshold(mock_filter, sample_matrix):
    """Test with a custom threshold."""
    with patch("mcp_server.tools.availability_check.AvailabilityFilter", return_value=mock_filter), \
         patch("mcp_server.tools.availability_check.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.availability_check import run_tool

        inp = CheckAvailabilityInput(threshold=0.5)
        result = await run_tool(inp)

    assert isinstance(result, CheckAvailabilityOutput)


@pytest.mark.asyncio
async def test_availability_gene_subset(mock_filter, sample_matrix):
    """Test filtering with a specific gene subset."""
    with patch("mcp_server.tools.availability_check.AvailabilityFilter", return_value=mock_filter):
        from mcp_server.tools.availability_check import run_tool

        inp = CheckAvailabilityInput(genes=["gene_0", "gene_1"])
        result = await run_tool(inp, expression_matrix=sample_matrix)

    assert isinstance(result, CheckAvailabilityOutput)


@pytest.mark.asyncio
async def test_availability_imputation_impact(mock_filter, sample_matrix):
    """Test imputation impact when both matrices provided."""
    imputed = sample_matrix.fillna(0)
    with patch("mcp_server.tools.availability_check.AvailabilityFilter", return_value=mock_filter):
        from mcp_server.tools.availability_check import run_tool

        inp = CheckAvailabilityInput()
        result = await run_tool(inp, expression_matrix=sample_matrix, imputed_matrix=imputed)

    assert "genes_rescued" in result.imputation_impact


@pytest.mark.asyncio
async def test_availability_serialization(mock_filter, sample_matrix):
    """Test output serialization."""
    with patch("mcp_server.tools.availability_check.AvailabilityFilter", return_value=mock_filter), \
         patch("mcp_server.tools.availability_check.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.availability_check import run_tool

        inp = CheckAvailabilityInput()
        result = await run_tool(inp)

    dumped = result.model_dump()
    assert "available" in dumped
    assert "filtered" in dumped
