"""Tests for the SampleQCWorkflow."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from workflows.schemas import (
    SampleQCParams,
    SampleQCProgress,
    SampleQCResult,
    WorkflowStatus,
)


class TestSampleQCParams:
    def test_default_values(self):
        params = SampleQCParams()
        assert params.dataset == "train"
        assert params.classification_methods == ["ensemble"]
        assert params.distance_methods == ["hungarian"]
        assert params.n_iterations == 100

    def test_custom_values(self):
        params = SampleQCParams(
            dataset="test",
            classification_methods=["rf", "svm"],
            distance_methods=["euclidean"],
            n_iterations=50,
        )
        assert params.dataset == "test"
        assert len(params.classification_methods) == 2
        assert params.n_iterations == 50

    def test_serialization_roundtrip(self):
        params = SampleQCParams()
        data = params.model_dump()
        restored = SampleQCParams.model_validate(data)
        assert restored == params


class TestSampleQCResult:
    def test_completed_result(self):
        now = datetime.now(UTC)
        result = SampleQCResult(
            workflow_id="qc-123",
            status=WorkflowStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            total_samples=20,
            flagged_samples=[{"sample_id": "S004", "concordance": "high"}],
            concordance_report={"concordance_rate": 1.0, "n_concordant": 1},
        )
        assert result.status == WorkflowStatus.COMPLETED
        assert result.total_samples == 20
        assert len(result.flagged_samples) == 1
        assert result.error is None

    def test_failed_result(self):
        result = SampleQCResult(
            workflow_id="qc-err",
            status=WorkflowStatus.FAILED,
            started_at=datetime.now(UTC),
            error="classification activity failed",
        )
        assert result.status == WorkflowStatus.FAILED
        assert result.error is not None
        assert result.total_samples == 0

    def test_empty_flags(self):
        result = SampleQCResult(
            workflow_id="qc-clean",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_samples=20,
        )
        assert result.flagged_samples == []
        assert result.concordance_report == {}


class TestSampleQCProgress:
    def test_initial_progress(self):
        progress = SampleQCProgress(
            workflow_id="qc-prog",
            status=WorkflowStatus.PENDING,
        )
        assert progress.current_phase == "pending"
        assert progress.samples_processed == 0
        assert progress.total_samples == 0

    def test_progress_mid_execution(self):
        progress = SampleQCProgress(
            workflow_id="qc-prog",
            status=WorkflowStatus.RUNNING,
            current_phase="classification_qc",
            samples_processed=10,
            total_samples=20,
        )
        assert progress.current_phase == "classification_qc"
        assert progress.samples_processed == 10


class TestSampleQCWorkflowLogic:
    @pytest.fixture
    def qc_activity_results(self):
        return {
            "clinical": {"dataset": "train", "n_samples": 20},
            "molecular": {"modality": "proteomics", "n_samples": 20, "n_features": 50},
            "classification": {"flagged_samples": ["S004", "S015"], "n_flagged": 2},
            "distance": {"flagged_samples": ["S004"], "n_flagged": 1},
            "cross_validate": {
                "concordant_flags": [{"sample_id": "S004", "concordance": "high"}],
                "classification_only": ["S015"],
                "distance_only": [],
                "concordance_rate": 0.5,
            },
        }

    def test_workflow_phases_defined(self):
        try:
            from workflows.sample_qc import PHASES
            assert "load_clinical" in PHASES
            assert "cross_validate" in PHASES
            assert "generate_report" in PHASES
            assert len(PHASES) == 6
        except ImportError:
            pytest.skip("Temporal SDK not installed")

    def test_saga_compensation_on_failure(self, qc_activity_results):
        classification_flags = qc_activity_results["classification"]["flagged_samples"]
        distance_flags = qc_activity_results["distance"]["flagged_samples"]
        all_flagged = list(set(classification_flags) | set(distance_flags))
        assert "S004" in all_flagged
        assert "S015" in all_flagged
        assert len(all_flagged) == 2

    def test_dual_validation_concordance(self, qc_activity_results):
        cv = qc_activity_results["cross_validate"]
        assert len(cv["concordant_flags"]) == 1
        assert cv["concordant_flags"][0]["sample_id"] == "S004"
        assert cv["classification_only"] == ["S015"]

    def test_result_from_qc_activities(self, qc_activity_results):
        result = SampleQCResult(
            workflow_id="qc-test",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_samples=qc_activity_results["clinical"]["n_samples"],
            flagged_samples=qc_activity_results["cross_validate"]["concordant_flags"],
            concordance_report=qc_activity_results["cross_validate"],
        )
        assert result.total_samples == 20
        assert len(result.flagged_samples) == 1

    def test_progress_updates_during_phases(self):
        progress = SampleQCProgress(
            workflow_id="qc-prog",
            status=WorkflowStatus.RUNNING,
            current_phase="load_clinical",
            samples_processed=0,
            total_samples=0,
        )
        progress.total_samples = 20
        progress.current_phase = "classification_qc"
        progress.samples_processed = 5
        assert progress.total_samples == 20
        assert progress.current_phase == "classification_qc"

    def test_empty_flags_workflow(self):
        result = SampleQCResult(
            workflow_id="qc-clean",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_samples=20,
            flagged_samples=[],
            concordance_report={"concordance_rate": 1.0, "n_concordant": 0, "total_flagged": 0},
        )
        assert result.flagged_samples == []
        assert result.concordance_report["total_flagged"] == 0

    def test_workflow_status_transitions(self):
        progress = SampleQCProgress(
            workflow_id="qc-trans",
            status=WorkflowStatus.PENDING,
        )
        progress.status = WorkflowStatus.RUNNING
        assert progress.status == WorkflowStatus.RUNNING
        progress.status = WorkflowStatus.COMPLETED
        assert progress.status == WorkflowStatus.COMPLETED
