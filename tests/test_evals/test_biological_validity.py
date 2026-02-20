"""Tests for the BiologicalValidityEval evaluator."""

from pathlib import Path

import pytest

from evals.biological_validity import BiologicalValidityEval

FIXTURES_PATH = str(Path(__file__).resolve().parent.parent.parent / "evals" / "fixtures" / "known_msi_signatures.json")


@pytest.fixture
def evaluator():
    return BiologicalValidityEval(fixtures_path=FIXTURES_PATH)


# Pathway genes for reference:
# immune_infiltration: PTPRC, ITGB2, LCP1, NCF2
# interferon_response: GBP1, GBP4, IRF1, IFI35, WARS
# antigen_presentation: TAP1, TAPBP, LAG3
# mismatch_repair_adjacent: CIITA, TYMP


class TestBiologicalValidityEval:
    def test_full_pathway_coverage(self, evaluator):
        """All 4 pathways covered -> score 1.0, PASS."""
        genes = ["PTPRC", "GBP1", "TAP1", "CIITA"]
        result = evaluator.evaluate(genes)
        assert result.passed is True
        assert result.score == 1.0
        assert result.name == "biological_validity"
        assert result.details["pathways_covered"] == 4
        assert result.details["total_pathways"] == 4

    def test_partial_pathway_coverage(self, evaluator):
        """Cover 2 of 4 pathways -> score 0.5."""
        genes = ["PTPRC", "TAP1"]
        result = evaluator.evaluate(genes)
        assert result.score == 0.5
        assert result.details["pathways_covered"] == 2

    def test_no_coverage(self, evaluator):
        """Empty panel -> score 0, FAIL."""
        result = evaluator.evaluate([])
        assert result.passed is False
        assert result.score == 0.0
        assert result.details["pathways_covered"] == 0

    def test_single_gene_covers_pathway(self, evaluator):
        """A single gene from a pathway is enough to cover it."""
        genes = ["NCF2"]  # Only in immune_infiltration
        result = evaluator.evaluate(genes)
        assert result.score == 0.25  # 1 of 4 pathways
        assert result.details["pathway_details"]["immune_infiltration"]["covered"] is True
        assert result.details["pathway_details"]["interferon_response"]["covered"] is False

    def test_threshold_boundary_pass(self, evaluator):
        """Score exactly at threshold should pass (>=)."""
        # 3 of 4 = 0.75, threshold 0.75
        genes = ["PTPRC", "GBP1", "TAP1"]
        result = evaluator.evaluate(genes, threshold=0.75)
        assert result.passed is True
        assert result.score == 0.75

    def test_threshold_boundary_fail(self, evaluator):
        """Score just below threshold should fail."""
        # 2 of 4 = 0.5, threshold 0.75
        genes = ["PTPRC", "GBP1"]
        result = evaluator.evaluate(genes, threshold=0.75)
        assert result.passed is False
        assert result.score == 0.5

    def test_custom_threshold(self, evaluator):
        """Custom threshold of 0.25 should pass with 1 pathway covered."""
        genes = ["CIITA"]  # Only mismatch_repair_adjacent
        result = evaluator.evaluate(genes, threshold=0.25)
        assert result.passed is True
        assert result.score == 0.25

    def test_pathway_details_structure(self, evaluator):
        """Verify the pathway_details dict has expected keys and structure."""
        genes = ["PTPRC", "ITGB2", "GBP1"]
        result = evaluator.evaluate(genes)
        details = result.details["pathway_details"]

        assert set(details.keys()) == {
            "immune_infiltration",
            "interferon_response",
            "antigen_presentation",
            "mismatch_repair_adjacent",
        }

        immune = details["immune_infiltration"]
        assert immune["covered"] is True
        assert "PTPRC" in immune["genes_found"]
        assert "ITGB2" in immune["genes_found"]
        assert isinstance(immune["genes_expected"], list)

        antigen = details["antigen_presentation"]
        assert antigen["covered"] is False
        assert antigen["genes_found"] == []
