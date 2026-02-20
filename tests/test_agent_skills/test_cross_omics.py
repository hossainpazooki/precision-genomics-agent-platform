"""Tests for agent_skills.cross_omics_integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent_skills.cross_omics_integration import CrossOmicsIntegrationSkill


def _make_tool_caller(responses: dict) -> AsyncMock:
    async def caller(tool_name, **kwargs):
        return responses.get(tool_name, {})

    return AsyncMock(side_effect=caller)


@pytest.fixture
def tool_responses():
    return {
        "load_dataset": {
            "samples": 20,
            "features": {"proteomics": 50, "rnaseq": 60},
            "msi_distribution": {"MSI-H": 3, "MSS": 17},
            "gender_distribution": {"Male": 10, "Female": 10},
            "missing_data_summary": {},
        },
        "impute_missing_values": {
            "genes_before": 50,
            "genes_imputed_mar": 3,
            "genes_assigned_mnar_zero": 0,
            "nmf_reconstruction_error": 0.001,
            "features_recovered": 48,
            "comparison": {},
        },
        "check_availability": {
            "available": ["gene_0", "gene_1"],
            "filtered": [],
            "availability_scores": {},
            "imputation_impact": {},
        },
        "match_cross_omics_samples": {
            "distance_matrix_info": {"shape": [20, 20]},
            "identified_mismatches": [{"sample_id": "S003"}],
            "iteration_agreement": 0.93,
        },
        "run_classification": {
            "ensemble_f1": 0.90,
            "per_classifier_f1": {"svm": 0.88},
            "best_strategy": "both",
            "strategy_comparison": {},
            "feature_importances": [],
            "comparison_to_baseline": {},
        },
        "evaluate_model": {
            "f1_score": 0.87,
            "precision": 0.89,
            "recall": 0.85,
            "confusion_matrix": [[15, 2], [1, 2]],
            "roc_auc": 0.91,
            "baseline_comparison": {"baseline_f1": 0.50, "improvement": 0.37},
        },
    }


@pytest.mark.asyncio
async def test_integration_runs(tool_responses):
    """Test full integration pipeline completes."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run()

    assert "steps" in result
    assert "summary" in result


@pytest.mark.asyncio
async def test_integration_summary_fields(tool_responses):
    """Test summary contains expected fields."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run()

    summary = result["summary"]
    assert summary["n_samples"] == 20
    assert summary["ensemble_f1"] == 0.90
    assert summary["eval_f1"] == 0.87
    assert summary["n_mismatches"] == 1


@pytest.mark.asyncio
async def test_integration_impute_both_modalities(tool_responses):
    """Test that imputation runs for both modalities."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run()

    assert "impute_proteomics" in result["steps"]
    assert "impute_rnaseq" in result["steps"]


@pytest.mark.asyncio
async def test_integration_calls_evaluator(tool_responses):
    """Test that the evaluator is called."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run()

    assert "evaluate_model" in result["steps"]
    assert result["steps"]["evaluate_model"]["f1_score"] == 0.87


@pytest.mark.asyncio
async def test_integration_iteration_agreement(tool_responses):
    """Test iteration agreement is in summary."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run()

    assert result["summary"]["iteration_agreement"] == 0.93


@pytest.mark.asyncio
async def test_integration_custom_config(tool_responses):
    """Test with custom config."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run(config={"cv_folds": 5, "target": "mismatch"})

    assert result["dataset"] == "train"


@pytest.mark.asyncio
async def test_integration_no_caller_raises():
    """Test that running without tool_caller raises RuntimeError."""
    skill = CrossOmicsIntegrationSkill(tool_caller=None)
    with pytest.raises(RuntimeError, match="No tool_caller"):
        await skill.run()


@pytest.mark.asyncio
async def test_integration_all_steps_present(tool_responses):
    """Test that all pipeline steps are in the result."""
    caller = _make_tool_caller(tool_responses)
    skill = CrossOmicsIntegrationSkill(tool_caller=caller)
    result = await skill.run()

    expected_steps = [
        "load_dataset",
        "impute_proteomics",
        "impute_rnaseq",
        "check_availability",
        "match_cross_omics",
        "run_classification",
        "evaluate_model",
    ]
    for step in expected_steps:
        assert step in result["steps"], f"Missing step: {step}"
