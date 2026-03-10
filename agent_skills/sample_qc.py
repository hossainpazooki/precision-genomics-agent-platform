"""Agent skill: Sample QC and mismatch detection.

Two independent paths for detecting sample mismatches:
  Path A: Classification-based (ensemble classifier on sample features)
  Path B: Distance-matrix matching (cross-omics correlation)
Cross-validates both and reports concordance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class SampleQCSkill:
    """Detect mislabeled or swapped samples via dual-path analysis."""

    def __init__(self, tool_caller: Callable | None = None) -> None:
        self.tool_caller = tool_caller

    async def _call_tool(self, tool_name: str, **kwargs: Any) -> dict:
        if self.tool_caller is None:
            raise RuntimeError("No tool_caller configured for SampleQCSkill")
        result = self.tool_caller(tool_name, **kwargs)
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def run(self, dataset: str = "train", config: dict | None = None) -> dict:
        """Run dual-path sample QC analysis.

        Path A: classification-based detection
        Path B: distance matrix matching
        Then cross-validate both paths.
        """
        config = config or {}
        report: dict[str, Any] = {"dataset": dataset, "paths": {}}

        # Load dataset first
        load_result = await self._call_tool(
            "load_dataset",
            dataset=dataset,
            modalities=["clinical", "proteomics", "rnaseq"],
        )
        report["n_samples"] = load_result.get("samples", 0)

        # Impute before analysis
        await self._call_tool(
            "impute_missing",
            dataset=dataset,
            modality="proteomics",
            strategy=config.get("impute_strategy", "nmf"),
        )

        # Path A: Classification-based mismatch detection
        classify_result = await self._call_tool(
            "run_classification",
            target="mismatch",
            phenotype_strategy="both",
            cv_folds=config.get("cv_folds", 10),
        )
        report["paths"]["classification"] = {
            "ensemble_f1": classify_result.get("ensemble_f1", 0.0),
            "per_classifier_f1": classify_result.get("per_classifier_f1", {}),
            "best_strategy": classify_result.get("best_strategy", "unknown"),
        }

        # Path B: Cross-omics distance matching
        match_result = await self._call_tool(
            "match_cross_omics",
            dataset=dataset,
            distance_method=config.get("distance_method", "both"),
            n_iterations=config.get("n_iterations", 100),
            gene_sampling_fraction=config.get("gene_sampling_fraction", 0.8),
        )
        report["paths"]["distance_matrix"] = {
            "distance_matrix_info": match_result.get("distance_matrix_info", {}),
            "identified_mismatches": match_result.get("identified_mismatches", []),
            "iteration_agreement": match_result.get("iteration_agreement", 0.0),
        }

        # Cross-validate: find samples flagged by both paths
        flagged_ids = {m.get("sample_id") for m in match_result.get("identified_mismatches", []) if m.get("sample_id")}

        # Concordance analysis
        report["concordance"] = {
            "classification_f1": classify_result.get("ensemble_f1", 0.0),
            "flagged_by_distance": sorted(flagged_ids),
            "n_flagged_distance": len(flagged_ids),
            "iteration_agreement": match_result.get("iteration_agreement", 0.0),
        }

        # Overall QC verdict
        n_flagged = len(flagged_ids)
        if n_flagged == 0:
            report["verdict"] = "PASS"
            report["confidence"] = "high"
        elif n_flagged <= 2:
            report["verdict"] = "WARNING"
            report["confidence"] = "medium"
        else:
            report["verdict"] = "FAIL"
            report["confidence"] = "high"

        return report
