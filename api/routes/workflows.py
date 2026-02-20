"""Generic workflow management endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from workflows.schemas import WorkflowStatus

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Shared mock store with analysis routes
_mock_runs: dict[str, dict] = {}

VALID_WORKFLOW_TYPES = {"biomarker_discovery", "sample_qc"}


@router.post("/run")
async def run_workflow(workflow_type: str, params: dict | None = None) -> dict:
    """Start a workflow by type name."""
    if workflow_type not in VALID_WORKFLOW_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow type: {workflow_type}. "
            f"Valid types: {', '.join(sorted(VALID_WORKFLOW_TYPES))}",
        )

    workflow_id = f"{workflow_type}-{uuid.uuid4().hex[:12]}"

    try:
        from temporalio.client import Client

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        client = await Client.connect(config.host, namespace=config.namespace)

        if workflow_type == "biomarker_discovery":
            from workflows.biomarker_discovery import BiomarkerDiscoveryWorkflow
            from workflows.schemas import BiomarkerDiscoveryParams

            wf_params = BiomarkerDiscoveryParams(**(params or {}))
            handle = await client.start_workflow(
                BiomarkerDiscoveryWorkflow.run,
                wf_params,
                id=workflow_id,
                task_queue=config.task_queue,
            )
        elif workflow_type == "sample_qc":
            from workflows.sample_qc import SampleQCWorkflow
            from workflows.schemas import SampleQCParams

            wf_params = SampleQCParams(**(params or {}))
            handle = await client.start_workflow(
                SampleQCWorkflow.run,
                wf_params,
                id=workflow_id,
                task_queue=config.task_queue,
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown workflow type")

        return {
            "workflow_id": workflow_id,
            "run_id": handle.result_run_id,
            "status": WorkflowStatus.RUNNING,
        }
    except HTTPException:
        raise
    except Exception:
        _mock_runs[workflow_id] = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "status": WorkflowStatus.PENDING,
            "params": params or {},
            "started_at": datetime.now(UTC).isoformat(),
        }
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.PENDING,
            "message": "Workflow queued (Temporal unavailable, using mock)",
        }


@router.get("/{workflow_id}/status")
async def get_workflow_status(workflow_id: str) -> dict:
    """Get the status of a workflow execution."""
    if workflow_id in _mock_runs:
        run = _mock_runs[workflow_id]
        return {
            "workflow_id": workflow_id,
            "workflow_type": run["workflow_type"],
            "status": run["status"],
            "started_at": run["started_at"],
        }

    # Try to look up in analysis mock store
    from api.routes.analysis import _mock_workflows

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
        raise HTTPException(
            status_code=404, detail=f"Workflow {workflow_id} not found"
        )


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str) -> dict:
    """Cancel a running workflow."""
    if workflow_id in _mock_runs:
        _mock_runs[workflow_id]["status"] = WorkflowStatus.CANCELLED
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.CANCELLED,
            "message": "Workflow cancelled",
        }

    from api.routes.analysis import _mock_workflows

    if workflow_id in _mock_workflows:
        _mock_workflows[workflow_id]["status"] = WorkflowStatus.CANCELLED
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.CANCELLED,
            "message": "Workflow cancelled",
        }

    try:
        from temporalio.client import Client

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        client = await Client.connect(config.host, namespace=config.namespace)
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
        return {
            "workflow_id": workflow_id,
            "status": WorkflowStatus.CANCELLED,
            "message": "Workflow cancel requested",
        }
    except Exception:
        raise HTTPException(
            status_code=404, detail=f"Workflow {workflow_id} not found"
        )
