"""Generic workflow management endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from workflows.schemas import WorkflowStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Shared mock store with analysis routes
_mock_runs: dict[str, dict] = {}

VALID_WORKFLOW_TYPES = {"biomarker_discovery", "sample_qc", "prompt_optimization", "cosmo_pipeline"}


def _is_gcp_available() -> bool:
    """Check if GCP Workflows client is available."""
    try:
        from google.cloud.workflows.executions_v1 import ExecutionsClient  # noqa: F401

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        return config.project is not None
    except ImportError:
        return False


def _get_workflow_id_for_type(config, workflow_type: str) -> str:
    """Map workflow type to GCP Workflow ID."""
    mapping = {
        "biomarker_discovery": config.biomarker_discovery_id,
        "sample_qc": config.sample_qc_id,
        "prompt_optimization": config.prompt_optimization_id,
    }
    return mapping[workflow_type]


@router.post("/run")
async def run_workflow(workflow_type: str, params: dict | None = None) -> dict:
    """Start a workflow by type name."""
    if workflow_type not in VALID_WORKFLOW_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workflow type: {workflow_type}. Valid types: {', '.join(sorted(VALID_WORKFLOW_TYPES))}",
        )

    workflow_id = f"{workflow_type}-{uuid.uuid4().hex[:12]}"

    if _is_gcp_available():
        try:
            from google.cloud.workflows.executions_v1 import ExecutionsClient
            from google.cloud.workflows.executions_v1.types import Execution

            from workflows.config import WorkflowConfig

            config = WorkflowConfig()
            client = ExecutionsClient()
            gcp_workflow_id = _get_workflow_id_for_type(config, workflow_type)
            parent = (
                f"projects/{config.project}/locations/{config.location}"
                f"/workflows/{gcp_workflow_id}"
            )

            import json

            execution_args = {
                **(params or {}),
                "activity_service_url": config.activity_service_url,
                "workflow_id": workflow_id,
            }

            execution = client.create_execution(
                parent=parent,
                execution=Execution(argument=json.dumps(execution_args)),
            )

            return {
                "workflow_id": workflow_id,
                "execution_name": execution.name,
                "status": WorkflowStatus.RUNNING,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("GCP Workflows call failed, falling back to local: %s", exc)

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
        "message": "Workflow queued (using local runner)",
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

    # Try progress table
    try:
        from workflows.progress import get_progress

        progress = await get_progress(workflow_id)
        if progress:
            return progress
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


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

    # Try GCP Workflows cancellation
    if _is_gcp_available():
        try:
            from google.cloud.workflows.executions_v1 import ExecutionsClient

            client = ExecutionsClient()
            client.cancel_execution(name=workflow_id)
            return {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.CANCELLED,
                "message": "Workflow cancel requested",
            }
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
