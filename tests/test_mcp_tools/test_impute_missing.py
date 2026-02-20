"""Tests for mcp_server.tools.impute_missing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from mcp_server.schemas.omics import ImputeMissingInput, ImputeMissingOutput


@pytest.fixture
def sample_matrix():
    """Create a sample expression matrix with some NaNs."""
    rng = np.random.RandomState(42)
    data = rng.lognormal(2.0, 1.5, (20, 30))
    df = pd.DataFrame(data, columns=[f"gene_{i}" for i in range(30)])
    df.iloc[0, 0] = np.nan
    df.iloc[5, 10] = np.nan
    df.iloc[10, 20] = np.nan
    return df


@pytest.fixture
def sample_clinical():
    """Create sample clinical data."""
    return pd.DataFrame({
        "sample_id": [f"S{i:03d}" for i in range(20)],
        "MSI_status": ["MSI-H"] * 3 + ["MSS"] * 17,
        "gender": ["Male"] * 10 + ["Female"] * 10,
    })


@pytest.fixture
def mock_imputer(sample_matrix):
    """Create a mock OmicsImputer."""
    imputer = MagicMock()
    imputed = sample_matrix.fillna(0)
    stats = {
        "n_mar": 3, "n_mnar": 0, "total_missing": 3,
        "remaining_nan": 0, "pct_mnar": 0.0, "pct_mar": 100.0,
    }
    imputer.impute.return_value = (imputed, stats)
    return imputer


@pytest.mark.asyncio
async def test_impute_default(mock_imputer, sample_matrix, sample_clinical):
    """Test imputation with default parameters."""
    with patch("mcp_server.tools.impute_missing.OmicsImputer", return_value=mock_imputer), \
         patch("mcp_server.tools.impute_missing.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_clinical.return_value = sample_clinical
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.impute_missing import run_tool

        inp = ImputeMissingInput()
        result = await run_tool(inp)

    assert isinstance(result, ImputeMissingOutput)
    assert result.genes_before == 30


@pytest.mark.asyncio
async def test_impute_mar_count(mock_imputer, sample_matrix, sample_clinical):
    """Test that MAR gene count is returned."""
    with patch("mcp_server.tools.impute_missing.OmicsImputer", return_value=mock_imputer), \
         patch("mcp_server.tools.impute_missing.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_clinical.return_value = sample_clinical
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.impute_missing import run_tool

        inp = ImputeMissingInput()
        result = await run_tool(inp)

    assert result.genes_imputed_mar == 3


@pytest.mark.asyncio
async def test_impute_reconstruction_error(mock_imputer, sample_matrix, sample_clinical):
    """Test that reconstruction error is computed."""
    with patch("mcp_server.tools.impute_missing.OmicsImputer", return_value=mock_imputer), \
         patch("mcp_server.tools.impute_missing.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_clinical.return_value = sample_clinical
        loader.load_proteomics.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.impute_missing import run_tool

        inp = ImputeMissingInput()
        result = await run_tool(inp)

    assert isinstance(result.nmf_reconstruction_error, float)


@pytest.mark.asyncio
async def test_impute_with_preloaded_data(mock_imputer, sample_matrix, sample_clinical):
    """Test imputation with pre-loaded data."""
    with patch("mcp_server.tools.impute_missing.OmicsImputer", return_value=mock_imputer):
        from mcp_server.tools.impute_missing import run_tool

        inp = ImputeMissingInput()
        result = await run_tool(inp, expression_matrix=sample_matrix, clinical_df=sample_clinical)

    assert result.genes_before == 30


@pytest.mark.asyncio
async def test_impute_comparison_dict(mock_imputer, sample_matrix, sample_clinical):
    """Test that comparison statistics are returned."""
    with patch("mcp_server.tools.impute_missing.OmicsImputer", return_value=mock_imputer):
        from mcp_server.tools.impute_missing import run_tool

        inp = ImputeMissingInput()
        result = await run_tool(inp, expression_matrix=sample_matrix, clinical_df=sample_clinical)

    assert "total_missing_before" in result.comparison
    assert "pct_mar" in result.comparison


@pytest.mark.asyncio
async def test_impute_rnaseq_modality(mock_imputer, sample_matrix, sample_clinical):
    """Test imputation with RNA-Seq modality loads the correct data."""
    with patch("mcp_server.tools.impute_missing.OmicsImputer", return_value=mock_imputer), \
         patch("mcp_server.tools.impute_missing.OmicsDataLoader") as MockLoader:
        loader = MagicMock()
        loader.load_clinical.return_value = sample_clinical
        loader.load_rnaseq.return_value = sample_matrix
        MockLoader.return_value = loader

        from mcp_server.tools.impute_missing import run_tool

        inp = ImputeMissingInput(modality="rnaseq")
        result = await run_tool(inp)

    loader.load_rnaseq.assert_called_once()
    assert result.genes_before == 30
