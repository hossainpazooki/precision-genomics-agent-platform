"""Tests for mcp_server.tools.data_loader."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from mcp_server.schemas.omics import LoadDatasetInput, LoadDatasetOutput


@pytest.fixture
def mock_loader():
    """Create a mock OmicsDataLoader."""
    loader = MagicMock()
    loader.load_clinical.return_value = pd.DataFrame({
        "sample_id": [f"S{i:03d}" for i in range(20)],
        "MSI_status": ["MSI-H"] * 3 + ["MSS"] * 17,
        "gender": ["Male"] * 10 + ["Female"] * 10,
    })
    loader.load_proteomics.return_value = pd.DataFrame(
        np.random.rand(20, 50),
        columns=[f"gene_{i}" for i in range(50)],
    )
    loader.load_rnaseq.return_value = pd.DataFrame(
        np.random.rand(20, 60),
        columns=[f"gene_{i}" for i in range(60)],
    )
    return loader


@pytest.mark.asyncio
async def test_load_dataset_default(mock_loader):
    """Test loading dataset with default parameters."""
    with patch("mcp_server.tools.data_loader.OmicsDataLoader", return_value=mock_loader):
        from mcp_server.tools.data_loader import run_tool

        inp = LoadDatasetInput()
        result = await run_tool(inp)

    assert isinstance(result, LoadDatasetOutput)
    assert result.samples == 20


@pytest.mark.asyncio
async def test_load_dataset_msi_distribution(mock_loader):
    """Test that MSI distribution is reported."""
    with patch("mcp_server.tools.data_loader.OmicsDataLoader", return_value=mock_loader):
        from mcp_server.tools.data_loader import run_tool

        inp = LoadDatasetInput(modalities=["clinical", "proteomics"])
        result = await run_tool(inp)

    assert "MSI-H" in result.msi_distribution or "MSS" in result.msi_distribution


@pytest.mark.asyncio
async def test_load_dataset_gender_distribution(mock_loader):
    """Test that gender distribution is reported."""
    with patch("mcp_server.tools.data_loader.OmicsDataLoader", return_value=mock_loader):
        from mcp_server.tools.data_loader import run_tool

        inp = LoadDatasetInput(modalities=["clinical"])
        result = await run_tool(inp)

    assert "Male" in result.gender_distribution or "Female" in result.gender_distribution


@pytest.mark.asyncio
async def test_load_dataset_proteomics_features(mock_loader):
    """Test that proteomics feature count is reported."""
    with patch("mcp_server.tools.data_loader.OmicsDataLoader", return_value=mock_loader):
        from mcp_server.tools.data_loader import run_tool

        inp = LoadDatasetInput(modalities=["clinical", "proteomics"])
        result = await run_tool(inp)

    assert "proteomics" in result.features
    assert result.features["proteomics"] == 50


@pytest.mark.asyncio
async def test_load_dataset_missing_file(mock_loader):
    """Test graceful handling when a modality file is missing."""
    mock_loader.load_rnaseq.side_effect = FileNotFoundError("No RNA-Seq file")
    with patch("mcp_server.tools.data_loader.OmicsDataLoader", return_value=mock_loader):
        from mcp_server.tools.data_loader import run_tool

        inp = LoadDatasetInput(modalities=["clinical", "proteomics", "rnaseq"])
        result = await run_tool(inp)

    assert "rnaseq" not in result.features


@pytest.mark.asyncio
async def test_load_dataset_serialization(mock_loader):
    """Test that output serializes to dict."""
    with patch("mcp_server.tools.data_loader.OmicsDataLoader", return_value=mock_loader):
        from mcp_server.tools.data_loader import run_tool

        inp = LoadDatasetInput()
        result = await run_tool(inp)

    dumped = result.model_dump()
    assert isinstance(dumped, dict)
    assert "samples" in dumped
