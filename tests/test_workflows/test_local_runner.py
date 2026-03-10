"""Tests for the LocalWorkflowRunner."""

from __future__ import annotations

from workflows.local_runner import LocalWorkflowRunner
from workflows.schemas import WorkflowStatus


class TestLocalWorkflowRunner:
    def test_instantiation(self):
        runner = LocalWorkflowRunner()
        assert runner._executions == {}

    def test_has_all_workflow_methods(self):
        runner = LocalWorkflowRunner()
        assert hasattr(runner, "run_biomarker_discovery")
        assert hasattr(runner, "run_sample_qc")
        assert hasattr(runner, "run_prompt_optimization")

    def test_get_execution_not_found(self):
        runner = LocalWorkflowRunner()
        assert runner.get_execution("nonexistent") is None


class TestWorkflowConfig:
    def test_default_config(self):
        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        assert config.location == "us-central1"
        assert config.activity_service_url == "http://localhost:8081"
        assert config.project is None

    def test_workflow_ids(self):
        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        assert "biomarker" in config.biomarker_discovery_id
        assert "sample-qc" in config.sample_qc_id
        assert "prompt" in config.prompt_optimization_id


class TestWorkflowInfo:
    def test_execution_name_field(self):
        from datetime import UTC, datetime

        from workflows.schemas import WorkflowInfo

        info = WorkflowInfo(
            workflow_id="wf-123",
            workflow_type="biomarker_discovery",
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(UTC),
            execution_name="projects/p/locations/l/workflows/w/executions/e",
        )
        assert info.execution_name is not None
        assert "task_queue" not in info.model_dump()
