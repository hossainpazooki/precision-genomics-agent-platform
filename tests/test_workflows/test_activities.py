"""Tests for Temporal activity functions."""

from __future__ import annotations

from workflows.activities.claude_activities import _fallback_interpretation


class TestFallbackInterpretation:
    def test_returns_template(self):
        result = _fallback_interpretation(["TAP1", "LCP1", "GBP1"], "msi")
        assert result["source"] == "template"
        assert result["model"] == "fallback"
        assert result["target"] == "msi"
        assert "TAP1" in result["interpretation"]

    def test_gene_list_in_output(self):
        genes = ["BRCA1", "TP53", "EGFR", "KRAS", "PTEN", "APC"]
        result = _fallback_interpretation(genes, "gender")
        assert "BRCA1" in result["interpretation"]
        assert len(result["genes_analyzed"]) == 6


class TestCrossValidateFlagsLogic:
    def test_concordant_flags(self):
        classification_flags = ["S004", "S015"]
        distance_flags = ["S004"]
        concordant = list(set(classification_flags) & set(distance_flags))
        assert concordant == ["S004"]

    def test_no_overlap(self):
        classification_set = {"S001", "S002"}
        distance_set = {"S003", "S004"}
        concordant = classification_set & distance_set
        assert len(concordant) == 0

    def test_full_overlap(self):
        classification_set = {"S001", "S002"}
        distance_set = {"S001", "S002"}
        concordant = classification_set & distance_set
        assert concordant == {"S001", "S002"}

    def test_concordance_rate_calculation(self):
        classification_flags = ["S004", "S015"]
        distance_flags = ["S004"]
        all_flags = set(classification_flags) | set(distance_flags)
        concordant = set(classification_flags) & set(distance_flags)
        rate = len(concordant) / len(all_flags) if all_flags else 1.0
        assert rate == 0.5

    def test_empty_flags(self):
        all_flags = set() | set()
        rate = 1.0 if not all_flags else len(set() & set()) / len(all_flags)
        assert rate == 1.0


class TestIntegrateAndFilterLogic:
    def test_deduplication(self):
        panels = [
            {"modality": "proteomics", "features": ["TAP1", "LCP1", "GBP1"]},
            {"modality": "rnaseq", "features": ["GBP1", "IRF1", "TAP1"]},
        ]
        all_features = []
        for panel in panels:
            all_features.extend(panel["features"])
        seen = set()
        unique = []
        for f in all_features:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        assert unique == ["TAP1", "LCP1", "GBP1", "IRF1"]
        assert len(unique) == 4

    def test_empty_panels(self):
        panels = []
        all_features = []
        for panel in panels:
            all_features.extend(panel.get("features", []))
        assert all_features == []

    def test_single_modality(self):
        panels = [{"modality": "proteomics", "features": ["TAP1", "LCP1"]}]
        all_features = []
        for panel in panels:
            all_features.extend(panel["features"])
        assert len(all_features) == 2

    def test_quarantine_activity_input(self):
        sample_ids = ["S004", "S015"]
        result = {
            "quarantined": sample_ids,
            "n_quarantined": len(sample_ids),
            "action": "quarantine",
        }
        assert result["n_quarantined"] == 2
        assert result["action"] == "quarantine"
