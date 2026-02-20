"""Tests for agent_skills.literature_grounding."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_skills.literature_grounding import LiteratureGroundingSkill


@pytest.mark.asyncio
async def test_grounding_no_http_client():
    """Test grounding without HTTP client returns mock results."""
    skill = LiteratureGroundingSkill()
    result = await skill.run(genes=["TAP1", "GBP1"], context="MSI")

    assert result["n_genes"] == 2
    assert len(result["results"]) == 2
    assert result["results"][0]["literature"]["source"] == "mock"


@pytest.mark.asyncio
async def test_grounding_heuristic_confidence():
    """Test heuristic confidence classification without LLM."""
    skill = LiteratureGroundingSkill()
    result = await skill.run(genes=["TAP1"], context="MSI")

    synthesis = result["results"][0]["synthesis"]
    assert synthesis["confidence"] in ("high", "medium", "low")
    assert synthesis["source"] == "heuristic"


@pytest.mark.asyncio
async def test_grounding_with_http_client():
    """Test grounding with a mock HTTP client."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "esearchresult": {
            "count": "15",
            "idlist": ["12345", "67890", "11111"],
        }
    }

    http_client = AsyncMock()
    http_client.get.return_value = mock_response

    skill = LiteratureGroundingSkill(http_client=http_client)
    result = await skill.run(genes=["TAP1"], context="MSI")

    lit = result["results"][0]["literature"]
    assert lit["pmid_count"] == 15
    assert lit["source"] == "pubmed"
    assert len(lit["top_pmids"]) == 3


@pytest.mark.asyncio
async def test_grounding_http_error():
    """Test graceful handling of HTTP errors."""
    http_client = AsyncMock()
    http_client.get.side_effect = ConnectionError("Network error")

    skill = LiteratureGroundingSkill(http_client=http_client)
    result = await skill.run(genes=["TAP1"], context="MSI")

    lit = result["results"][0]["literature"]
    assert lit["source"] == "error"
    assert lit["pmid_count"] == 0


@pytest.mark.asyncio
async def test_grounding_overall_confidence():
    """Test overall confidence aggregation."""
    skill = LiteratureGroundingSkill()
    result = await skill.run(genes=["TAP1", "GBP1", "BRCA1"], context="MSI")

    assert result["overall_confidence"] in ("high", "medium", "low", "none")


@pytest.mark.asyncio
async def test_grounding_empty_genes():
    """Test with empty gene list."""
    skill = LiteratureGroundingSkill()
    result = await skill.run(genes=[], context="MSI")

    assert result["n_genes"] == 0
    assert result["overall_confidence"] == "none"


@pytest.mark.asyncio
async def test_grounding_confidence_counts():
    """Test confidence count fields."""
    skill = LiteratureGroundingSkill()
    result = await skill.run(genes=["TAP1", "GBP1"], context="MSI")

    total = result["n_high_confidence"] + result["n_medium_confidence"] + result["n_low_confidence"]
    assert total == result["n_genes"]


@pytest.mark.asyncio
async def test_grounding_context_propagated():
    """Test that context is propagated to all results."""
    skill = LiteratureGroundingSkill()
    result = await skill.run(genes=["TAP1"], context="colorectal_cancer")

    assert result["context"] == "colorectal_cancer"
    assert result["results"][0]["literature"]["query"] == "TAP1 AND colorectal_cancer"
