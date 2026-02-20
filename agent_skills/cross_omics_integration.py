"""Agent skill: Cross-omics integration pipeline.

Delegates to ``core.pipeline.COSMOInspiredPipeline`` for the full
COSMO-inspired multi-omics integration workflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class CrossOmicsIntegrationSkill:
    """Run end-to-end cross-omics integration using the COSMO pipeline."""

    def __init__(self, tool_caller: Callable | None = None) -> None:
        self.tool_caller = tool_caller

    async def _call_tool(self, tool_name: str, **kwargs: Any) -> dict:
        if self.tool_caller is None:
            raise RuntimeError("No tool_caller configured for CrossOmicsIntegrationSkill")
        result = self.tool_caller(tool_name, **kwargs)
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def run(
        self,
        dataset: str = "train",
        config: dict | None = None,
    ) -> dict:
        """Run the cross-omics integration pipeline.

        Steps:
            1. Load both modalities
            2. Impute missing values for each
            3. Check gene availability
            4. Cross-omics matching to find shared genes
            5. Classification on integrated features
            6. Evaluation
        """
        config = config or {}
        report: dict[str, Any] = {"dataset": dataset, "steps": {}}

        # Step 1: Load dataset
        load_result = await self._call_tool(
            "load_dataset",
            dataset=dataset,
            modalities=["clinical", "proteomics", "rnaseq"],
        )
        report["steps"]["load_dataset"] = load_result

        # Step 2: Impute both modalities
        for modality in ("proteomics", "rnaseq"):
            impute_result = await self._call_tool(
                "impute_missing_values",
                dataset=dataset,
                modality=modality,
                strategy=config.get("impute_strategy", "nmf"),
            )
            report["steps"][f"impute_{modality}"] = impute_result

        # Step 3: Availability check
        avail_result = await self._call_tool(
            "check_availability",
            threshold=config.get("availability_threshold", 0.9),
            dataset=dataset,
            use_imputed=True,
        )
        report["steps"]["check_availability"] = avail_result

        # Step 4: Cross-omics matching
        match_result = await self._call_tool(
            "match_cross_omics_samples",
            dataset=dataset,
            distance_method=config.get("distance_method", "both"),
            n_iterations=config.get("n_iterations", 100),
            gene_sampling_fraction=config.get("gene_sampling_fraction", 0.8),
        )
        report["steps"]["match_cross_omics"] = match_result

        # Step 5: Classification on integrated features
        classify_result = await self._call_tool(
            "run_classification",
            target=config.get("target", "mismatch"),
            phenotype_strategy="both",
            cv_folds=config.get("cv_folds", 10),
        )
        report["steps"]["run_classification"] = classify_result

        # Step 6: Evaluation
        eval_result = await self._call_tool(
            "evaluate_model",
            model_id="ensemble",
            test_data=config.get("test_data", "holdout"),
            compare_to_baseline=True,
        )
        report["steps"]["evaluate_model"] = eval_result

        # Summary
        report["summary"] = {
            "n_samples": load_result.get("samples", 0),
            "n_mismatches": len(match_result.get("identified_mismatches", [])),
            "iteration_agreement": match_result.get("iteration_agreement", 0.0),
            "ensemble_f1": classify_result.get("ensemble_f1", 0.0),
            "eval_f1": eval_result.get("f1_score", 0.0),
        }

        return report
