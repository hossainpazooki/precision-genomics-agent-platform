"""Tests for agent_skills.biomarker_discovery."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent_skills.biomarker_discovery import BiomarkerDiscoverySkill


def _make_tool_caller(responses: dict) -> AsyncMock:
    """Create a mock tool caller that returns preset responses keyed by tool name."""

    async def caller(tool_name, **kwargs):
        return responses.get(tool_name, {})

    return AsyncMock(side_effect=caller)


@pytest.fixture
def tool_responses():
    """Standard tool responses for biomarker discovery."""
    return {
        "load_dataset": {
            "samples": 20,
            "features": {"proteomics": 50, "rnaseq": 60},
            "msi_distribution": {"MSI-H": 3, "MSS": 17},
            "gender_distribution": {"Male": 10, "Female": 10},
            "missing_data_summary": {"proteomics": 10.5, "rnaseq": 8.2},
        },
        "impute_missing": {
            "genes_before": 50,
            "genes_imputed_mar": 5,
            "genes_assigned_mnar_zero": 2,
            "nmf_reconstruction_error": 0.001,
            "features_recovered": 48,
            "comparison": {"total_missing_before": 100.0, "remaining_nan": 0.0},
        },
        "check_availability": {
            "available": ["gene_0", "gene_1"],
            "filtered": ["gene_2"],
            "availability_scores": {"gene_0": 0.95},
            "imputation_impact": {},
        },
        "select_biomarkers": {
            "biomarkers": [
                {"gene": "TAP1", "score": 0.95, "rank": 1},
                {"gene": "GBP1", "score": 0.90, "rank": 2},
            ],
            "method_agreement": {"anova": ["TAP1", "GBP1"]},
            "comparison_to_original": {"overlap_count": 2.0},
        },
        "run_classification": {
            "ensemble_f1": 0.92,
            "per_classifier_f1": {"svm": 0.88},
            "best_strategy": "both",
            "strategy_comparison": {"both": 0.92},
            "feature_importances": [],
            "comparison_to_baseline": {"baseline_f1": 0.50},
        },
        "match_cross_omics": {
            "distance_matrix_info": {"shape": [20, 20]},
            "identified_mismatches": [{"sample_id": "S003"}],
            "iteration_agreement": 0.95,
        },
        "explain_features": {
            "explanations": [
                {"gene": "TAP1", "known_msi_marker": True},
                {"gene": "GBP1", "known_msi_marker": True},
            ],
        },
    }


@pytest.mark.asyncio
async def test_skill_runs_successfully(tool_responses):
    """Test that the skill completes the full pipeline."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    result = await skill.run()

    assert "steps" in result
    assert "summary" in result


@pytest.mark.asyncio
async def test_skill_reports_samples(tool_responses):
    """Test that sample count is in the summary."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    result = await skill.run()

    assert result["summary"]["n_samples"] == 20


@pytest.mark.asyncio
async def test_skill_reports_features(tool_responses):
    """Test that feature count is in the summary."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    result = await skill.run()

    assert result["summary"]["n_features_selected"] == 2


@pytest.mark.asyncio
async def test_skill_reports_f1(tool_responses):
    """Test that ensemble F1 is in the summary."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    result = await skill.run()

    assert result["summary"]["ensemble_f1"] == 0.92


@pytest.mark.asyncio
async def test_skill_reports_mismatches(tool_responses):
    """Test that mismatch count is in the summary."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    result = await skill.run()

    assert result["summary"]["n_mismatches"] == 1


@pytest.mark.asyncio
async def test_skill_calls_all_tools(tool_responses):
    """Test that all expected tools are called."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    await skill.run()

    called_tools = [call.args[0] for call in caller.call_args_list]
    assert "load_dataset" in called_tools
    assert "impute_missing" in called_tools
    assert "check_availability" in called_tools
    assert "select_biomarkers" in called_tools
    assert "run_classification" in called_tools
    assert "match_cross_omics" in called_tools
    assert "explain_features" in called_tools


@pytest.mark.asyncio
async def test_skill_no_caller_raises():
    """Test that running without tool_caller raises RuntimeError."""
    skill = BiomarkerDiscoverySkill(tool_caller=None)
    with pytest.raises(RuntimeError, match="No tool_caller"):
        await skill.run()


@pytest.mark.asyncio
async def test_skill_custom_target(tool_responses):
    """Test with a custom target."""
    caller = _make_tool_caller(tool_responses)
    skill = BiomarkerDiscoverySkill(tool_caller=caller)
    result = await skill.run(target="gender")

    assert result["target"] == "gender"
