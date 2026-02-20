"""Tests for the ReproducibilityEval evaluator."""

import pytest

from evals.reproducibility import ReproducibilityEval


@pytest.fixture
def evaluator():
    return ReproducibilityEval()


class TestReproducibilityEval:
    def test_deterministic_pipeline(self, evaluator):
        """Identical results every run -> Jaccard 1.0, PASS."""
        fixed_genes = ["GENE_A", "GENE_B", "GENE_C", "GENE_D", "GENE_E"]

        def deterministic_pipeline(seed=0):
            return fixed_genes

        result = evaluator.evaluate(deterministic_pipeline, n_runs=5, top_k=5, threshold=0.85)
        assert result.passed is True
        assert result.score == 1.0
        assert result.name == "reproducibility"

    def test_stochastic_pipeline(self, evaluator):
        """Each run returns completely different genes -> low Jaccard."""
        def stochastic_pipeline(seed=0):
            return [f"GENE_{seed}_{i}" for i in range(10)]

        result = evaluator.evaluate(stochastic_pipeline, n_runs=5, top_k=10, threshold=0.85)
        assert result.passed is False
        assert result.score == 0.0

    def test_threshold_pass(self, evaluator):
        """Mostly overlapping results should pass with low threshold."""
        base = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

        def mostly_stable(seed=0):
            # Change only last element per seed
            return base[:-1] + [f"X{seed}"]

        result = evaluator.evaluate(mostly_stable, n_runs=5, top_k=10, threshold=0.50)
        assert result.passed is True
        assert result.score > 0.50

    def test_threshold_fail(self, evaluator):
        """Even somewhat stable results fail with very high threshold."""
        base = ["A", "B", "C", "D", "E"]

        def somewhat_stable(seed=0):
            # Change 2 of 5 each run
            return base[:3] + [f"X{seed}", f"Y{seed}"]

        result = evaluator.evaluate(somewhat_stable, n_runs=5, top_k=5, threshold=0.99)
        assert result.passed is False

    def test_single_run(self, evaluator):
        """n_runs=1 -> no pairs, avg_jaccard=0, should fail."""
        def pipeline(seed=0):
            return ["A", "B", "C"]

        result = evaluator.evaluate(pipeline, n_runs=1, top_k=3, threshold=0.85)
        assert result.passed is False
        assert result.score == 0
        assert result.details["pairwise_jaccard_scores"] == []

    def test_empty_features(self, evaluator):
        """Pipeline returning empty results -> all Jaccard = 1.0 (0|0 = 0)."""
        def empty_pipeline(seed=0):
            return []

        result = evaluator.evaluate(empty_pipeline, n_runs=3, top_k=5, threshold=0.85)
        assert result.passed is True
        assert result.score == 1.0

    def test_details_structure(self, evaluator):
        """Verify the details dict has all expected keys."""
        def pipeline(seed=0):
            return ["A", "B", "C"]

        result = evaluator.evaluate(pipeline, n_runs=3, top_k=3, threshold=0.85)
        assert "n_runs" in result.details
        assert "top_k" in result.details
        assert "pairwise_jaccard_scores" in result.details
        assert "min_jaccard" in result.details
        assert "max_jaccard" in result.details
        assert result.details["n_runs"] == 3
        assert result.details["top_k"] == 3
        # 3 runs -> C(3,2) = 3 pairs
        assert len(result.details["pairwise_jaccard_scores"]) == 3
