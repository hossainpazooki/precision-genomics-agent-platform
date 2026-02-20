"""Agent skill: End-to-end biomarker discovery workflow.

Orchestrates the full pipeline from data loading through feature explanation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class BiomarkerDiscoverySkill:
    """Orchestrate biomarker discovery across the full MCP tool chain."""

    def __init__(self, tool_caller: Callable | None = None) -> None:
        self.tool_caller = tool_caller

    async def _call_tool(self, tool_name: str, **kwargs: Any) -> dict:
        """Call an MCP tool or raise if no caller configured."""
        if self.tool_caller is None:
            raise RuntimeError("No tool_caller configured for BiomarkerDiscoverySkill")
        result = self.tool_caller(tool_name, **kwargs)
        if hasattr(result, "__await__"):
            result = await result
        return result

    async def run(
        self,
        target: str = "msi",
        modalities: list[str] | None = None,
        config: dict | None = None,
    ) -> dict:
        """Orchestrate: load -> impute -> availability -> select -> classify -> match -> explain -> report."""
        modalities = modalities or ["proteomics", "rnaseq"]
        config = config or {}
        report: dict[str, Any] = {"target": target, "modalities": modalities, "steps": {}}

        # Step 1: Load dataset
        load_result = await self._call_tool(
            "load_dataset",
            dataset=config.get("dataset", "train"),
            modalities=["clinical"] + modalities,
            data_dir=config.get("data_dir"),
        )
        report["steps"]["load_dataset"] = load_result

        # Step 2: Impute missing values (per modality)
        impute_results: dict[str, Any] = {}
        for modality in modalities:
            impute_result = await self._call_tool(
                "impute_missing_values",
                dataset=config.get("dataset", "train"),
                modality=modality,
                strategy=config.get("impute_strategy", "nmf"),
                classify_missingness=True,
            )
            impute_results[modality] = impute_result
        report["steps"]["impute_missing"] = impute_results

        # Step 3: Availability check
        avail_result = await self._call_tool(
            "check_availability",
            threshold=config.get("availability_threshold", 0.9),
            dataset=config.get("dataset", "train"),
            use_imputed=True,
        )
        report["steps"]["check_availability"] = avail_result

        # Step 4: Select biomarkers (per modality)
        selection_results: dict[str, Any] = {}
        for modality in modalities:
            sel_result = await self._call_tool(
                "select_biomarkers",
                target=target,
                modality=modality,
                integration=config.get("integration", "union_weighted"),
                n_top=config.get("n_top", 30),
            )
            selection_results[modality] = sel_result
        report["steps"]["select_biomarkers"] = selection_results

        # Step 5: Run classification
        classify_result = await self._call_tool(
            "run_classification",
            target=config.get("classification_target", "mismatch"),
            phenotype_strategy=config.get("phenotype_strategy", "both"),
            cv_folds=config.get("cv_folds", 10),
        )
        report["steps"]["run_classification"] = classify_result

        # Step 6: Cross-omics matching
        match_result = await self._call_tool(
            "match_cross_omics_samples",
            dataset=config.get("dataset", "train"),
            distance_method=config.get("distance_method", "both"),
            n_iterations=config.get("n_iterations", 100),
            gene_sampling_fraction=config.get("gene_sampling_fraction", 0.8),
        )
        report["steps"]["match_cross_omics"] = match_result

        # Step 7: Explain top features
        all_genes: list[str] = []
        for modality_result in selection_results.values():
            for biomarker in modality_result.get("biomarkers", []):
                gene = biomarker.get("gene")
                if gene and gene not in all_genes:
                    all_genes.append(gene)

        if all_genes:
            explain_result = await self._call_tool(
                "explain_features",
                genes=all_genes[:30],
                context=f"{target}_classification",
                include_provenance=True,
            )
            report["steps"]["explain_features"] = explain_result

        # Summary
        report["summary"] = {
            "n_samples": load_result.get("samples", 0),
            "n_features_selected": len(all_genes),
            "ensemble_f1": classify_result.get("ensemble_f1", 0.0),
            "n_mismatches": len(match_result.get("identified_mismatches", [])),
        }

        return report
