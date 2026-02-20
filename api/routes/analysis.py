"""Analysis workflow endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from workflows.schemas import (
    BiomarkerDiscoveryParams,
    SampleQCParams,
    WorkflowStatus,
)

router = APIRouter(prefix="/analyze", tags=["Analysis"])

# In-memory store for demo/testing when Temporal is not available
_mock_workflows: dict[str, dict] = {}


def _get_temporal_client():
    """Try to get a Temporal client, return None if unavailable."""
    try:
        from temporalio.client import Client  # noqa: F401

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        return config
    except ImportError:
        return None


@router.post("/biomarkers")
async def start_biomarker_analysis(params: BiomarkerDiscoveryParams) -> dict:
    """Start a biomarker discovery workflow."""
    workflow_id = f"biomarker-{uuid.uuid4().hex[:12]}"

    try:
        from temporalio.client import Client

        from workflows.biomarker_discovery import BiomarkerDiscoveryWorkflow
        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        client = await Client.connect(config.host, namespace=config.namespace)
        handle = await client.start_workflow(
            BiomarkerDiscoveryWorkflow.run,
            params,
            id=workflow_id,
            task_queue=config.task_queue,
        )
        return {
            "workflow_id": workflow_id,
            "run_id": handle.result_run_id,
            "status": WorkflowStatus.RUNNING,
            "message": "Biomarker discovery workflow started",
        }
    except Exception:
        # Fallback: store in memory for testing
        _mock_workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "workflow_type": "biomarker_discovery",
            "status": WorkflowStatus.PENDING,
            "params": params.model_dump(),
            "started_at": datetime.now(UTC).isoformat(),
            "result": None,
        }
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.PENDING,
            "message": "Workflow queued (Temporal unavailable, using mock)",
        }


@router.post("/sample-qc")
async def start_sample_qc(params: SampleQCParams) -> dict:
    """Start a sample QC workflow."""
    workflow_id = f"sample-qc-{uuid.uuid4().hex[:12]}"

    try:
        from temporalio.client import Client

        from workflows.config import WorkflowConfig
        from workflows.sample_qc import SampleQCWorkflow

        config = WorkflowConfig()
        client = await Client.connect(config.host, namespace=config.namespace)
        handle = await client.start_workflow(
            SampleQCWorkflow.run,
            params,
            id=workflow_id,
            task_queue=config.task_queue,
        )
        return {
            "workflow_id": workflow_id,
            "run_id": handle.result_run_id,
            "status": WorkflowStatus.RUNNING,
            "message": "Sample QC workflow started",
        }
    except Exception:
        _mock_workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "workflow_type": "sample_qc",
            "status": WorkflowStatus.PENDING,
            "params": params.model_dump(),
            "started_at": datetime.now(UTC).isoformat(),
            "result": None,
        }
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.PENDING,
            "message": "Workflow queued (Temporal unavailable, using mock)",
        }


@router.get("/{workflow_id}/status")
async def get_analysis_status(workflow_id: str) -> dict:
    """Get the status of an analysis workflow."""
    # Check mock store first
    if workflow_id in _mock_workflows:
        wf = _mock_workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "workflow_type": wf["workflow_type"],
            "status": wf["status"],
            "started_at": wf["started_at"],
        }

    try:
        from temporalio.client import Client

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        client = await Client.connect(config.host, namespace=config.namespace)
        handle = client.get_workflow_handle(workflow_id)
        desc = await handle.describe()
        return {
            "workflow_id": workflow_id,
            "status": desc.status.name.lower() if desc.status else "unknown",
            "run_id": desc.run_id,
        }
    except Exception:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found") from None


@router.get("/{workflow_id}/report")
async def get_analysis_report(workflow_id: str) -> dict:
    """Get the final report for a completed workflow."""
    if workflow_id in _mock_workflows:
        wf = _mock_workflows[workflow_id]
        if wf["result"] is not None:
            return {"workflow_id": workflow_id, "report": wf["result"]}
        return {
            "workflow_id": workflow_id,
            "status": wf["status"],
            "message": "Workflow has not completed yet",
        }

    try:
        from temporalio.client import Client

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        client = await Client.connect(config.host, namespace=config.namespace)
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.result()
        return {"workflow_id": workflow_id, "report": result}
    except Exception:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found") from None
