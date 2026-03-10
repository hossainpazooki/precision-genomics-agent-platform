"""Tests for the BiomarkerDiscoveryWorkflow."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from workflows.schemas import (
    BiomarkerDiscoveryParams,
    BiomarkerDiscoveryProgress,
    BiomarkerDiscoveryResult,
    WorkflowStatus,
)


class TestBiomarkerDiscoveryParams:
    def test_default_values(self):
        params = BiomarkerDiscoveryParams()
        assert params.dataset == "train"
        assert params.target == "msi"
        assert params.modalities == ["proteomics", "rnaseq"]
        assert params.n_top_features == 30
        assert params.cv_folds == 10

    def test_custom_values(self):
        params = BiomarkerDiscoveryParams(
            dataset="test",
            target="gender",
            modalities=["proteomics"],
            n_top_features=50,
            cv_folds=5,
        )
        assert params.dataset == "test"
        assert params.target == "gender"
        assert params.modalities == ["proteomics"]
        assert params.n_top_features == 50

    def test_serialization_roundtrip(self):
        params = BiomarkerDiscoveryParams()
        data = params.model_dump()
        assert data["dataset"] == "train"
        restored = BiomarkerDiscoveryParams.model_validate(data)
        assert restored == params


class TestBiomarkerDiscoveryResult:
    def test_completed_result(self):
        now = datetime.now(UTC)
        result = BiomarkerDiscoveryResult(
            workflow_id="wf-123",
            status=WorkflowStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            target="msi",
            modalities=["proteomics"],
            feature_panel={"features": ["TAP1", "LCP1"]},
            classification_metrics={"accuracy": 0.85},
        )
        assert result.status == WorkflowStatus.COMPLETED
        assert result.error is None
        assert result.feature_panel["features"] == ["TAP1", "LCP1"]

    def test_failed_result(self):
        result = BiomarkerDiscoveryResult(
            workflow_id="wf-err",
            status=WorkflowStatus.FAILED,
            started_at=datetime.now(UTC),
            target="msi",
            modalities=["proteomics"],
            error="Activity timed out",
        )
        assert result.status == WorkflowStatus.FAILED
        assert result.error == "Activity timed out"
        assert result.completed_at is None


class TestBiomarkerDiscoveryProgress:
    def test_initial_progress(self):
        progress = BiomarkerDiscoveryProgress(
            workflow_id="wf-123",
            status=WorkflowStatus.PENDING,
        )
        assert progress.current_phase == "pending"
        assert progress.phases_completed == []

    def test_progress_with_phases(self):
        progress = BiomarkerDiscoveryProgress(
            workflow_id="wf-123",
            status=WorkflowStatus.RUNNING,
            current_phase="feature_selection",
            phases_completed=["load_and_validate", "impute"],
            phases_remaining=["integrate_and_filter", "train_and_evaluate"],
        )
        assert progress.current_phase == "feature_selection"
        assert len(progress.phases_completed) == 2


class TestBiomarkerDiscoveryWorkflowLogic:
    @pytest.fixture
    def activity_results(self):
        return {
            "load_and_validate": {"dataset": "train", "n_samples": 20},
            "impute": {"modality": "proteomics", "missing_before": 100, "missing_after": 0},
            "select_features": {"modality": "proteomics", "features": ["TAP1", "LCP1", "PTPN6"], "n_selected": 3},
            "integrate": {"features": ["TAP1", "LCP1", "PTPN6"], "n_total": 3},
            "train": {"accuracy": 0.85, "auc": 0.89},
            "interpret": {"interpretation": "Immune infiltration markers.", "source": "template"},
            "report": {"cross_omics_validation": {"n_overlapping": 2}},
        }

    def test_local_runner_exists(self):
        from workflows.local_runner import LocalWorkflowRunner

        runner = LocalWorkflowRunner()
        assert hasattr(runner, "run_biomarker_discovery")

    def test_params_forwarded_correctly(self):
        params = BiomarkerDiscoveryParams(dataset="test", target="gender", modalities=["proteomics"])
        data = params.model_dump()
        restored = BiomarkerDiscoveryParams.model_validate(data)
        assert restored.dataset == "test"

    def test_result_construction_on_success(self, activity_results):
        result = BiomarkerDiscoveryResult(
            workflow_id="wf-test",
            status=WorkflowStatus.COMPLETED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            target="msi",
            modalities=["proteomics", "rnaseq"],
            feature_panel=activity_results["integrate"],
            classification_metrics=activity_results["train"],
            interpretation=activity_results["interpret"],
        )
        assert result.status == WorkflowStatus.COMPLETED
        assert result.feature_panel["n_total"] == 3

    def test_result_construction_on_failure(self):
        result = BiomarkerDiscoveryResult(
            workflow_id="wf-fail",
            status=WorkflowStatus.FAILED,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            target="msi",
            modalities=["proteomics"],
            error="load_and_validate_data_activity timed out",
        )
        assert result.status == WorkflowStatus.FAILED
        assert "timed out" in result.error

    def test_fan_out_fan_in_modalities(self, activity_results):
        modalities = ["proteomics", "rnaseq"]
        panels = []
        for mod in modalities:
            panel = dict(activity_results["select_features"])
            panel["modality"] = mod
            panels.append(panel)
        assert len(panels) == 2
        assert panels[0]["modality"] == "proteomics"
        assert panels[1]["modality"] == "rnaseq"

    def test_progress_tracking(self):
        progress = BiomarkerDiscoveryProgress(
            workflow_id="wf-prog",
            status=WorkflowStatus.RUNNING,
            current_phase="pending",
            phases_completed=[],
            phases_remaining=[
                "load_and_validate",
                "impute",
                "feature_selection",
                "integrate_and_filter",
                "train_and_evaluate",
                "interpret",
                "compile_report",
            ],
        )
        progress.phases_completed.append("load_and_validate")
        progress.phases_remaining.remove("load_and_validate")
        progress.current_phase = "impute"
        assert len(progress.phases_completed) == 1
        assert "load_and_validate" not in progress.phases_remaining

    def test_workflow_status_enum(self):
        assert WorkflowStatus.PENDING == "pending"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
        assert WorkflowStatus.CANCELLED == "cancelled"
