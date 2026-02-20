"""Tests for mcp_server.tools.match_cross_omics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from mcp_server.schemas.omics import MatchCrossOmicsInput, MatchCrossOmicsOutput


@pytest.fixture
def shared_genes():
    return [f"gene_{i}" for i in range(15)]


@pytest.fixture
def sample_proteomics(shared_genes):
    rng = np.random.RandomState(42)
    return pd.DataFrame(
        rng.rand(20, 15),
        columns=shared_genes,
        index=[f"S{i:03d}" for i in range(20)],
    )


@pytest.fixture
def sample_rnaseq(shared_genes):
    rng = np.random.RandomState(99)
    return pd.DataFrame(
        rng.rand(20, 15),
        columns=shared_genes,
        index=[f"S{i:03d}" for i in range(20)],
    )


@pytest.fixture
def mock_matcher():
    """Create a mock CrossOmicsMatcher."""
    matcher = MagicMock()
    matcher.compute_gene_correlations.return_value = {
        "gene_0": 0.85,
        "gene_1": 0.72,
        "gene_2": 0.91,
    }
    dm = np.eye(20)
    matcher.build_distance_matrix.return_value = dm
    matcher.identify_mismatches.return_value = [
        {"sample_id": "S003", "agreement": 0.95, "distance": 0.8},
        {"sample_id": "S014", "agreement": 0.88, "distance": 0.7},
    ]
    return matcher


@pytest.mark.asyncio
async def test_match_default(mock_matcher, sample_proteomics, sample_rnaseq):
    """Test cross-omics matching with defaults."""
    with patch("core.cross_omics_matcher.CrossOmicsMatcher", return_value=mock_matcher):
        from mcp_server.tools.match_cross_omics import run_tool

        inp = MatchCrossOmicsInput()
        result = await run_tool(inp, proteomics_df=sample_proteomics, rnaseq_df=sample_rnaseq)

    assert isinstance(result, MatchCrossOmicsOutput)
    assert len(result.identified_mismatches) == 2


@pytest.mark.asyncio
async def test_match_distance_matrix_info(mock_matcher, sample_proteomics, sample_rnaseq):
    """Test that distance matrix info is returned."""
    with patch("core.cross_omics_matcher.CrossOmicsMatcher", return_value=mock_matcher):
        from mcp_server.tools.match_cross_omics import run_tool

        inp = MatchCrossOmicsInput()
        result = await run_tool(inp, proteomics_df=sample_proteomics, rnaseq_df=sample_rnaseq)

    assert "shape" in result.distance_matrix_info
    assert "method" in result.distance_matrix_info


@pytest.mark.asyncio
async def test_match_iteration_agreement(mock_matcher, sample_proteomics, sample_rnaseq):
    """Test iteration agreement computation."""
    with patch("core.cross_omics_matcher.CrossOmicsMatcher", return_value=mock_matcher):
        from mcp_server.tools.match_cross_omics import run_tool

        inp = MatchCrossOmicsInput()
        result = await run_tool(inp, proteomics_df=sample_proteomics, rnaseq_df=sample_rnaseq)

    assert 0 <= result.iteration_agreement <= 1.0


@pytest.mark.asyncio
async def test_match_flagged_samples(mock_matcher, sample_proteomics, sample_rnaseq):
    """Test that flagged samples are reported."""
    with patch("core.cross_omics_matcher.CrossOmicsMatcher", return_value=mock_matcher):
        from mcp_server.tools.match_cross_omics import run_tool

        inp = MatchCrossOmicsInput()
        result = await run_tool(inp, proteomics_df=sample_proteomics, rnaseq_df=sample_rnaseq)

    sample_ids = [m["sample_id"] for m in result.identified_mismatches]
    assert "S003" in sample_ids
    assert "S014" in sample_ids


@pytest.mark.asyncio
async def test_match_no_mismatches(sample_proteomics, sample_rnaseq):
    """Test when no mismatches are found."""
    matcher = MagicMock()
    matcher.compute_gene_correlations.return_value = {}
    matcher.build_distance_matrix.return_value = np.eye(20)
    matcher.identify_mismatches.return_value = []

    with patch("mcp_server.tools.match_cross_omics.CrossOmicsMatcher", return_value=matcher):
        from mcp_server.tools.match_cross_omics import run_tool

        inp = MatchCrossOmicsInput()
        result = await run_tool(inp, proteomics_df=sample_proteomics, rnaseq_df=sample_rnaseq)

    assert len(result.identified_mismatches) == 0
    assert result.iteration_agreement == 1.0


@pytest.mark.asyncio
async def test_match_serialization(mock_matcher, sample_proteomics, sample_rnaseq):
    """Test output serialization to dict."""
    with patch("core.cross_omics_matcher.CrossOmicsMatcher", return_value=mock_matcher):
        from mcp_server.tools.match_cross_omics import run_tool

        inp = MatchCrossOmicsInput()
        result = await run_tool(inp, proteomics_df=sample_proteomics, rnaseq_df=sample_rnaseq)

    dumped = result.model_dump()
    assert isinstance(dumped, dict)
    assert "distance_matrix_info" in dumped
    assert "identified_mismatches" in dumped
    assert "iteration_agreement" in dumped
