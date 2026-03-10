"""Local workflow runner for development without GCP Workflows.

Calls activity functions directly via asyncio, providing the same
execution semantics as the GCP Workflow YAML definitions.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from workflows.schemas import WorkflowStatus

logger = logging.getLogger(__name__)


class LocalWorkflowRunner:
    """Run workflows locally by calling activity functions directly."""

    def __init__(self) -> None:
        self._executions: dict[str, dict] = {}

    async def run_biomarker_discovery(
        self,
        dataset: str = "train",
        target: str = "msi",
        modalities: list[str] | None = None,
        n_top_features: int = 30,
    ) -> dict:
        """Execute the biomarker discovery workflow locally."""
        from workflows.activities.claude_activities import (
            compile_report_activity,
            generate_interpretation_activity,
        )
        from workflows.activities.data_activities import load_and_validate_data_activity
        from workflows.activities.ml_activities import (
            impute_data_activity,
            integrate_and_filter_activity,
            select_features_activity,
            train_and_evaluate_activity,
        )

        if modalities is None:
            modalities = ["proteomics", "rnaseq"]

        workflow_id = f"biomarker-{uuid.uuid4().hex[:12]}"
        self._executions[workflow_id] = {
            "status": WorkflowStatus.RUNNING,
            "started_at": datetime.now(UTC),
        }

        try:
            # Phase 1: Load and validate
            data_summary = await load_and_validate_data_activity(dataset, modalities)

            # Phase 2: Impute per modality (fan-out)
            imputation_results = await asyncio.gather(
                *[impute_data_activity(dataset, m) for m in modalities]
            )

            # Phase 3: Feature selection per modality (fan-out)
            feature_panels = await asyncio.gather(
                *[select_features_activity(dataset, target, m, n_top_features) for m in modalities]
            )

            # Phase 4: Integrate and filter (fan-in)
            integrated = await integrate_and_filter_activity(list(feature_panels))

            # Phase 5: Train and evaluate
            classification = await train_and_evaluate_activity(
                dataset, integrated.get("features", []), target
            )

            # Phase 6: Interpret
            interpretation = await generate_interpretation_activity(
                integrated.get("features", []), target
            )

            # Phase 7: Compile report
            report = await compile_report_activity(
                {
                    "data_summary": data_summary,
                    "imputation_results": list(imputation_results),
                    "feature_panels": list(feature_panels),
                    "integrated": integrated,
                    "classification": classification,
                    "interpretation": interpretation,
                }
            )

            self._executions[workflow_id]["status"] = WorkflowStatus.COMPLETED
            self._executions[workflow_id]["completed_at"] = datetime.now(UTC)

            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.COMPLETED,
                "report": report,
                "feature_panel": integrated,
                "classification_metrics": classification,
                "interpretation": interpretation,
            }

        except Exception as exc:
            self._executions[workflow_id]["status"] = WorkflowStatus.FAILED
            self._executions[workflow_id]["error"] = str(exc)
            raise

    async def run_sample_qc(
        self,
        dataset: str = "train",
        classification_methods: list[str] | None = None,
        n_iterations: int = 100,
    ) -> dict:
        """Execute the sample QC workflow locally."""
        from workflows.activities.claude_activities import compile_report_activity
        from workflows.activities.data_activities import (
            load_clinical_data_activity,
            load_molecular_data_activity,
            run_classification_qc_activity,
        )
        from workflows.activities.ml_activities import (
            cross_validate_flags_activity,
            quarantine_samples_activity,
            run_distance_matrix_activity,
        )

        if classification_methods is None:
            classification_methods = ["ensemble"]

        workflow_id = f"sample-qc-{uuid.uuid4().hex[:12]}"
        self._executions[workflow_id] = {
            "status": WorkflowStatus.RUNNING,
            "started_at": datetime.now(UTC),
        }

        flagged_by_classification: list[str] = []
        flagged_by_distance: list[str] = []

        try:
            clinical_data = await load_clinical_data_activity(dataset)
            await load_molecular_data_activity(dataset, "proteomics")

            classification_result = await run_classification_qc_activity(dataset, classification_methods)
            flagged_by_classification = classification_result.get("flagged_samples", [])

            distance_result = await run_distance_matrix_activity(dataset, n_iterations)
            flagged_by_distance = distance_result.get("flagged_samples", [])

            cross_validation = await cross_validate_flags_activity(
                flagged_by_classification, flagged_by_distance
            )

            report = await compile_report_activity(
                {
                    "clinical_data": clinical_data,
                    "classification_result": classification_result,
                    "distance_result": distance_result,
                    "cross_validation": cross_validation,
                }
            )

            self._executions[workflow_id]["status"] = WorkflowStatus.COMPLETED
            self._executions[workflow_id]["completed_at"] = datetime.now(UTC)

            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.COMPLETED,
                "report": report,
                "cross_validation": cross_validation,
                "total_samples": clinical_data.get("n_samples", 0),
            }

        except Exception as exc:
            self._executions[workflow_id]["status"] = WorkflowStatus.FAILED
            # Saga compensation
            all_flagged = list(set(flagged_by_classification) | set(flagged_by_distance))
            if all_flagged:
                try:
                    await quarantine_samples_activity(all_flagged)
                except Exception:
                    pass
            raise

    async def run_prompt_optimization(self, config: dict) -> dict:
        """Execute the prompt optimization workflow locally."""
        from workflows.activities.dspy_activities import (
            compare_and_deploy_activity,
            compile_dspy_modules_activity,
            generate_synthetic_cohort_activity,
            run_pipeline_with_prompts_activity,
        )

        workflow_id = f"prompt-opt-{uuid.uuid4().hex[:12]}"
        self._executions[workflow_id] = {
            "status": WorkflowStatus.RUNNING,
            "started_at": datetime.now(UTC),
        }

        try:
            # Step 1: Generate synthetic cohort
            cohort = await generate_synthetic_cohort_activity(config)

            # Step 2: Run baseline
            baseline_config = {**config, "prompt_version": "baseline"}
            baseline_results = await run_pipeline_with_prompts_activity(baseline_config)

            # Step 3: Compile DSPy modules
            compile_config = {
                "module": config.get("module", "biomarker_discovery"),
                "strategy": config.get("strategy", "mipro"),
                "training_path": config.get("training_path"),
            }
            compile_result = await compile_dspy_modules_activity(compile_config)

            if compile_result.get("status") == "skipped":
                return {
                    "workflow_id": workflow_id,
                    "status": "skipped",
                    "reason": compile_result.get("reason", "compilation skipped"),
                    "baseline": baseline_results,
                }

            # Step 4: Run optimized
            optimized_config = {**config, "prompt_version": "optimized"}
            optimized_results = await run_pipeline_with_prompts_activity(optimized_config)

            # Step 5: Compare and deploy
            deploy_config = {
                "module": config.get("module", "biomarker_discovery"),
                "baseline_score": baseline_results.get("auc", 0.0),
                "optimized_score": optimized_results.get("auc", 0.0),
                "improvement_threshold": config.get("improvement_threshold", 0.05),
            }
            deploy_result = await compare_and_deploy_activity(deploy_config)

            self._executions[workflow_id]["status"] = WorkflowStatus.COMPLETED
            self._executions[workflow_id]["completed_at"] = datetime.now(UTC)

            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "cohort": cohort,
                "baseline": baseline_results,
                "optimized": optimized_results,
                "compilation": compile_result,
                "deployment": deploy_result,
            }

        except Exception:
            self._executions[workflow_id]["status"] = WorkflowStatus.FAILED
            raise

    def get_execution(self, workflow_id: str) -> dict | None:
        """Get execution state by workflow ID."""
        return self._executions.get(workflow_id)
