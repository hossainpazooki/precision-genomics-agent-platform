"""Biomarker discovery workflow orchestrating multi-omics feature selection."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

try:
    import temporalio.workflow as workflow
    from temporalio.common import RetryPolicy

    HAS_TEMPORAL = True
except ImportError:
    HAS_TEMPORAL = False

if HAS_TEMPORAL:
    with workflow.unsafe.imports_passed_through():
        from workflows.schemas import (
            BiomarkerDiscoveryParams,
            BiomarkerDiscoveryProgress,
            BiomarkerDiscoveryResult,
            WorkflowStatus,
        )

    PHASES = [
        "load_and_validate",
        "impute",
        "feature_selection",
        "integrate_and_filter",
        "train_and_evaluate",
        "interpret",
        "compile_report",
    ]

    DEFAULT_RETRY = RetryPolicy(
        initial_interval=timedelta(seconds=1),
        maximum_interval=timedelta(seconds=30),
        maximum_attempts=3,
    )

    @workflow.defn
    class BiomarkerDiscoveryWorkflow:
        """Multi-phase biomarker discovery with fan-out/fan-in feature selection."""

        def __init__(self) -> None:
            self._progress = BiomarkerDiscoveryProgress(
                workflow_id="",
                status=WorkflowStatus.PENDING,
                current_phase="pending",
                phases_completed=[],
                phases_remaining=list(PHASES),
            )

        def _advance_phase(self, phase: str) -> None:
            self._progress.current_phase = phase
            self._progress.phases_completed.append(phase)
            self._progress.phases_remaining = [p for p in PHASES if p not in self._progress.phases_completed]

        @workflow.run
        async def run(self, params: BiomarkerDiscoveryParams) -> BiomarkerDiscoveryResult:
            wf_id = workflow.info().workflow_id
            self._progress.workflow_id = wf_id
            self._progress.status = WorkflowStatus.RUNNING
            started_at = datetime.now(UTC)

            try:
                # Phase 1: Load and validate data
                data_summary = await workflow.execute_activity(
                    "load_and_validate_data_activity",
                    args=[params.dataset, params.modalities],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                self._advance_phase("load_and_validate")

                # Phase 2: Impute missing data per modality
                impute_tasks = []
                for modality in params.modalities:
                    impute_tasks.append(
                        workflow.execute_activity(
                            "impute_data_activity",
                            args=[params.dataset, modality],
                            start_to_close_timeout=timedelta(minutes=10),
                            retry_policy=DEFAULT_RETRY,
                        )
                    )
                imputation_results = await asyncio.gather(*impute_tasks)
                self._advance_phase("impute")

                # Phase 3: Fan-out parallel feature selection per modality
                selection_tasks = []
                for modality in params.modalities:
                    selection_tasks.append(
                        workflow.execute_activity(
                            "select_features_activity",
                            args=[params.dataset, params.target, modality, params.n_top_features],
                            start_to_close_timeout=timedelta(minutes=15),
                            retry_policy=DEFAULT_RETRY,
                        )
                    )
                feature_panels = await asyncio.gather(*selection_tasks)
                self._advance_phase("feature_selection")

                # Phase 4: Fan-in: integrate and filter
                integrated = await workflow.execute_activity(
                    "integrate_and_filter_activity",
                    args=[list(feature_panels)],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                self._advance_phase("integrate_and_filter")

                # Phase 5: Train and evaluate classifier
                classification = await workflow.execute_activity(
                    "train_and_evaluate_activity",
                    args=[params.dataset, integrated.get("features", []), params.target],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=DEFAULT_RETRY,
                )
                self._advance_phase("train_and_evaluate")

                # Phase 6: Generate interpretation via Claude API
                interpretation = await workflow.execute_activity(
                    "generate_interpretation_activity",
                    args=[integrated.get("features", []), params.target],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        maximum_interval=timedelta(seconds=60),
                        maximum_attempts=3,
                    ),
                )
                self._advance_phase("interpret")

                # Phase 7: Compile final report
                report_input = {
                    "data_summary": data_summary,
                    "imputation_results": list(imputation_results),
                    "feature_panels": list(feature_panels),
                    "integrated": integrated,
                    "classification": classification,
                    "interpretation": interpretation,
                }
                report = await workflow.execute_activity(
                    "compile_report_activity",
                    args=[report_input],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                self._advance_phase("compile_report")

                self._progress.status = WorkflowStatus.COMPLETED

                return BiomarkerDiscoveryResult(
                    workflow_id=wf_id,
                    status=WorkflowStatus.COMPLETED,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    target=params.target,
                    modalities=params.modalities,
                    feature_panel=integrated,
                    classification_metrics=classification,
                    cross_omics_validation=report.get("cross_omics_validation", {}),
                    interpretation=interpretation,
                )

            except Exception as exc:
                self._progress.status = WorkflowStatus.FAILED
                return BiomarkerDiscoveryResult(
                    workflow_id=wf_id,
                    status=WorkflowStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    target=params.target,
                    modalities=params.modalities,
                    error=str(exc),
                )

        @workflow.query
        def get_progress(self) -> BiomarkerDiscoveryProgress:
            """Return current progress snapshot."""
            return self._progress
