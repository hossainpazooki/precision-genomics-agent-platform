"""Sample QC workflow with saga-pattern compensation."""

from __future__ import annotations

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
            SampleQCParams,
            SampleQCProgress,
            SampleQCResult,
            WorkflowStatus,
        )

    PHASES = [
        "load_clinical",
        "load_molecular",
        "classification_qc",
        "distance_matrix_qc",
        "cross_validate",
        "generate_report",
    ]

    DEFAULT_RETRY = RetryPolicy(
        initial_interval=timedelta(seconds=1),
        maximum_interval=timedelta(seconds=30),
        maximum_attempts=3,
    )

    @workflow.defn
    class SampleQCWorkflow:
        """Sample QC with dual-method validation and saga compensation."""

        def __init__(self) -> None:
            self._progress = SampleQCProgress(
                workflow_id="",
                status=WorkflowStatus.PENDING,
                current_phase="pending",
                samples_processed=0,
                total_samples=0,
            )

        @workflow.run
        async def run(self, params: SampleQCParams) -> SampleQCResult:
            wf_id = workflow.info().workflow_id
            self._progress.workflow_id = wf_id
            self._progress.status = WorkflowStatus.RUNNING
            started_at = datetime.now(UTC)

            completed_phases: list[str] = []
            flagged_by_classification: list[str] = []
            flagged_by_distance: list[str] = []

            try:
                # Phase 1: Load clinical data
                clinical_data = await workflow.execute_activity(
                    "load_clinical_data_activity",
                    args=[params.dataset],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                completed_phases.append("load_clinical")
                self._progress.current_phase = "load_clinical"
                self._progress.total_samples = clinical_data.get("n_samples", 0)

                # Phase 2: Load molecular data
                await workflow.execute_activity(
                    "load_molecular_data_activity",
                    args=[params.dataset, "proteomics"],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                completed_phases.append("load_molecular")
                self._progress.current_phase = "load_molecular"

                # Phase 3: Classification-based QC
                classification_result = await workflow.execute_activity(
                    "run_classification_qc_activity",
                    args=[params.dataset, params.classification_methods],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=DEFAULT_RETRY,
                )
                completed_phases.append("classification_qc")
                self._progress.current_phase = "classification_qc"
                flagged_by_classification = classification_result.get("flagged_samples", [])
                self._progress.samples_processed = len(flagged_by_classification)

                # Phase 4: Distance matrix QC
                distance_result = await workflow.execute_activity(
                    "run_distance_matrix_activity",
                    args=[params.dataset, params.n_iterations],
                    start_to_close_timeout=timedelta(minutes=20),
                    retry_policy=DEFAULT_RETRY,
                )
                completed_phases.append("distance_matrix_qc")
                self._progress.current_phase = "distance_matrix_qc"
                flagged_by_distance = distance_result.get("flagged_samples", [])

                # Phase 5: Cross-validate flags
                cross_validation = await workflow.execute_activity(
                    "cross_validate_flags_activity",
                    args=[flagged_by_classification, flagged_by_distance],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                completed_phases.append("cross_validate")
                self._progress.current_phase = "cross_validate"

                # Phase 6: Generate QC report
                report_input = {
                    "clinical_data": clinical_data,
                    "classification_result": classification_result,
                    "distance_result": distance_result,
                    "cross_validation": cross_validation,
                }
                await workflow.execute_activity(
                    "compile_report_activity",
                    args=[report_input],
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=DEFAULT_RETRY,
                )
                completed_phases.append("generate_report")
                self._progress.current_phase = "generate_report"
                self._progress.status = WorkflowStatus.COMPLETED

                return SampleQCResult(
                    workflow_id=wf_id,
                    status=WorkflowStatus.COMPLETED,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    total_samples=clinical_data.get("n_samples", 0),
                    flagged_samples=cross_validation.get("concordant_flags", []),
                    concordance_report=cross_validation,
                )

            except Exception as exc:
                self._progress.status = WorkflowStatus.FAILED

                # Saga compensation: quarantine flagged samples on failure
                all_flagged = list(set(flagged_by_classification) | set(flagged_by_distance))
                if all_flagged:
                    import contextlib

                    with contextlib.suppress(Exception):
                        await workflow.execute_activity(
                            "quarantine_samples_activity",
                            args=[all_flagged],
                            start_to_close_timeout=timedelta(minutes=5),
                            retry_policy=DEFAULT_RETRY,
                        )

                return SampleQCResult(
                    workflow_id=wf_id,
                    status=WorkflowStatus.FAILED,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    total_samples=self._progress.total_samples,
                    error=str(exc),
                )

        @workflow.query
        def get_progress(self) -> SampleQCProgress:
            """Return current progress snapshot."""
            return self._progress
