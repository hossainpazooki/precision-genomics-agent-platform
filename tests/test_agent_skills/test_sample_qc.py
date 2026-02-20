"""Tests for agent_skills.sample_qc."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent_skills.sample_qc import SampleQCSkill


def _make_tool_caller(responses: dict) -> AsyncMock:
    async def caller(tool_name, **kwargs):
        return responses.get(tool_name, {})

    return AsyncMock(side_effect=caller)


@pytest.fixture
def tool_responses_pass():
    """Responses resulting in a PASS verdict (no mismatches)."""
    return {
        "load_dataset": {
            "samples": 20,
            "features": {"proteomics": 50},
            "msi_distribution": {"MSI-H": 3, "MSS": 17},
            "gender_distribution": {"Male": 10, "Female": 10},
            "missing_data_summary": {},
        },
        "impute_missing_values": {
            "genes_before": 50,
            "genes_imputed_mar": 3,
            "genes_assigned_mnar_zero": 0,
            "nmf_reconstruction_error": 0.001,
            "features_recovered": 50,
            "comparison": {},
        },
        "run_classification": {
            "ensemble_f1": 0.95,
            "per_classifier_f1": {"svm": 0.93},
            "best_strategy": "both",
            "strategy_comparison": {},
            "feature_importances": [],
            "comparison_to_baseline": {},
        },
        "match_cross_omics_samples": {
            "distance_matrix_info": {"shape": [20, 20]},
            "identified_mismatches": [],
            "iteration_agreement": 1.0,
        },
    }


@pytest.fixture
def tool_responses_warning():
    """Responses resulting in a WARNING verdict (1-2 mismatches)."""
    responses = {
        "load_dataset": {
            "samples": 20,
            "features": {},
            "msi_distribution": {},
            "gender_distribution": {},
            "missing_data_summary": {},
        },
        "impute_missing_values": {
            "genes_before": 50,
            "genes_imputed_mar": 3,
            "genes_assigned_mnar_zero": 0,
            "nmf_reconstruction_error": 0.001,
            "features_recovered": 50,
            "comparison": {},
        },
        "run_classification": {
            "ensemble_f1": 0.85,
            "per_classifier_f1": {},
            "best_strategy": "both",
            "strategy_comparison": {},
            "feature_importances": [],
            "comparison_to_baseline": {},
        },
        "match_cross_omics_samples": {
            "distance_matrix_info": {},
            "identified_mismatches": [
                {"sample_id": "S003", "agreement": 0.9},
            ],
            "iteration_agreement": 0.85,
        },
    }
    return responses


@pytest.mark.asyncio
async def test_qc_pass(tool_responses_pass):
    """Test QC passes when no mismatches found."""
    caller = _make_tool_caller(tool_responses_pass)
    skill = SampleQCSkill(tool_caller=caller)
    result = await skill.run()

    assert result["verdict"] == "PASS"
    assert result["confidence"] == "high"


@pytest.mark.asyncio
async def test_qc_warning(tool_responses_warning):
    """Test QC gives WARNING for 1-2 mismatches."""
    caller = _make_tool_caller(tool_responses_warning)
    skill = SampleQCSkill(tool_caller=caller)
    result = await skill.run()

    assert result["verdict"] == "WARNING"
    assert result["confidence"] == "medium"


@pytest.mark.asyncio
async def test_qc_fail():
    """Test QC gives FAIL for many mismatches."""
    responses = {
        "load_dataset": {
            "samples": 20,
            "features": {},
            "msi_distribution": {},
            "gender_distribution": {},
            "missing_data_summary": {},
        },
        "impute_missing_values": {
            "genes_before": 50,
            "genes_imputed_mar": 0,
            "genes_assigned_mnar_zero": 0,
            "nmf_reconstruction_error": 0.0,
            "features_recovered": 50,
            "comparison": {},
        },
        "run_classification": {
            "ensemble_f1": 0.5,
            "per_classifier_f1": {},
            "best_strategy": "both",
            "strategy_comparison": {},
            "feature_importances": [],
            "comparison_to_baseline": {},
        },
        "match_cross_omics_samples": {
            "distance_matrix_info": {},
            "identified_mismatches": [{"sample_id": f"S{i:03d}"} for i in range(5)],
            "iteration_agreement": 0.6,
        },
    }
    caller = _make_tool_caller(responses)
    skill = SampleQCSkill(tool_caller=caller)
    result = await skill.run()

    assert result["verdict"] == "FAIL"
    assert result["confidence"] == "high"


@pytest.mark.asyncio
async def test_qc_concordance_fields(tool_responses_warning):
    """Test concordance fields are present."""
    caller = _make_tool_caller(tool_responses_warning)
    skill = SampleQCSkill(tool_caller=caller)
    result = await skill.run()

    assert "concordance" in result
    assert "flagged_by_distance" in result["concordance"]
    assert "n_flagged_distance" in result["concordance"]


@pytest.mark.asyncio
async def test_qc_dual_paths(tool_responses_pass):
    """Test both paths are reported."""
    caller = _make_tool_caller(tool_responses_pass)
    skill = SampleQCSkill(tool_caller=caller)
    result = await skill.run()

    assert "classification" in result["paths"]
    assert "distance_matrix" in result["paths"]


@pytest.mark.asyncio
async def test_qc_n_samples(tool_responses_pass):
    """Test n_samples is reported."""
    caller = _make_tool_caller(tool_responses_pass)
    skill = SampleQCSkill(tool_caller=caller)
    result = await skill.run()

    assert result["n_samples"] == 20


@pytest.mark.asyncio
async def test_qc_no_caller_raises():
    """Test that running without tool_caller raises RuntimeError."""
    skill = SampleQCSkill(tool_caller=None)
    with pytest.raises(RuntimeError, match="No tool_caller"):
        await skill.run()
