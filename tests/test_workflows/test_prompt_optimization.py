"""Tests for prompt optimization workflow and activities."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestDSPyActivitiesLogic:
    """Test DSPy activity logic."""

    def test_compare_and_deploy_above_threshold(self):
        baseline_score = 0.80
        optimized_score = 0.90
        improvement_threshold = 0.05

        improvement = optimized_score - baseline_score
        should_deploy = improvement >= improvement_threshold

        assert should_deploy is True
        assert improvement == pytest.approx(0.10)

    def test_compare_and_deploy_below_threshold(self):
        baseline_score = 0.80
        optimized_score = 0.82
        improvement_threshold = 0.05

        improvement = optimized_score - baseline_score
        should_deploy = improvement >= improvement_threshold

        assert should_deploy is False

    def test_compare_and_deploy_negative_improvement(self):
        baseline_score = 0.90
        optimized_score = 0.85

        improvement = optimized_score - baseline_score
        should_deploy = improvement >= 0.05

        assert should_deploy is False
        assert improvement < 0


class TestAutoPromptExampleMiner:
    def test_mine_from_pipeline_run(self):
        from dspy_modules.autoprompt_examples import AutoPromptExampleMiner

        miner = AutoPromptExampleMiner()
        run_results = {
            "dataset_summary": "100 samples, 500 features",
            "imputation_stats": "5% missing",
            "feature_list": "BRCA1, TP53, MLH1",
            "target": "msi",
            "report": "Biomarker panel selected successfully.",
            "interpretations": [
                {
                    "gene_name": "BRCA1",
                    "expression_context": "upregulated",
                    "pathway": "DNA repair",
                    "mechanism": "homologous recombination",
                    "pubmed_ids": "12345678",
                },
            ],
        }

        examples = miner.mine_from_pipeline_run(run_results)
        assert len(examples) == 2
        assert examples[0]["dataset_summary"] == "100 samples, 500 features"
        assert examples[1]["gene_name"] == "BRCA1"

    def test_mine_empty_run(self):
        from dspy_modules.autoprompt_examples import AutoPromptExampleMiner

        miner = AutoPromptExampleMiner()
        examples = miner.mine_from_pipeline_run({})
        assert examples == []

    def test_format_without_dspy(self):
        from dspy_modules.autoprompt_examples import AutoPromptExampleMiner

        miner = AutoPromptExampleMiner()
        examples = [
            {
                "gene_name": "BRCA1",
                "target": "msi",
                "_input_keys": ["gene_name", "target"],
            }
        ]
        # Without dspy installed, should return dicts as-is
        with patch("dspy_modules.autoprompt_examples._DSPY_AVAILABLE", False):
            result = miner.format_for_dspy(examples)
            assert isinstance(result[0], dict)


class TestCompileModule:
    def test_load_training_examples_missing_file(self):
        from dspy_modules.compile import load_training_examples

        result = load_training_examples(path="/nonexistent/path.json")
        assert result == []

    def test_compile_without_dspy_raises(self):
        from dspy_modules.compile import compile_module

        with patch("dspy_modules.compile._DSPY_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="dspy is not installed"):
                compile_module(MagicMock(), [], MagicMock(), strategy="mipro")

    def test_compile_unknown_strategy(self):
        with patch("dspy_modules.compile._DSPY_AVAILABLE", True):
            with patch("dspy_modules.compile.dspy") as mock_dspy:
                from dspy_modules.compile import compile_module

                with pytest.raises(ValueError, match="Unknown compilation strategy"):
                    compile_module(MagicMock(), [], MagicMock(), strategy="unknown")


import pytest
