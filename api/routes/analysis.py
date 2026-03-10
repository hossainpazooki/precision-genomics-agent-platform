"""Analysis workflow endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from workflows.schemas import (
    BiomarkerDiscoveryParams,
    SampleQCParams,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])

# In-memory store for local dev when GCP Workflows is not available
_mock_workflows: dict[str, dict] = {}


def _is_gcp_available() -> bool:
    """Check if GCP Workflows client is available."""
    try:
        from google.cloud.workflows.executions_v1 import ExecutionsClient  # noqa: F401

        from workflows.config import WorkflowConfig

        config = WorkflowConfig()
        return config.project is not None
    except ImportError:
        return False


@router.post("/biomarkers")
async def start_biomarker_analysis(params: BiomarkerDiscoveryParams) -> dict:
    """Start a biomarker discovery workflow."""
    workflow_id = f"biomarker-{uuid.uuid4().hex[:12]}"

    if _is_gcp_available():
        try:
            from google.cloud.workflows.executions_v1 import ExecutionsClient
            from google.cloud.workflows.executions_v1.types import Execution

            from workflows.config import WorkflowConfig

            config = WorkflowConfig()
            client = ExecutionsClient()
            parent = (
                f"projects/{config.project}/locations/{config.location}"
                f"/workflows/{config.biomarker_discovery_id}"
            )

            import json

            execution = client.create_execution(
                parent=parent,
                execution=Execution(
                    argument=json.dumps(
                        {
                            "dataset": params.dataset,
                            "target": params.target,
                            "modalities": params.modalities,
                            "n_top_features": params.n_top_features,
                            "activity_service_url": config.activity_service_url,
                            "workflow_id": workflow_id,
                        }
                    )
                ),
            )
            return {
                "workflow_id": workflow_id,
                "execution_name": execution.name,
                "status": WorkflowStatus.RUNNING,
                "message": "Biomarker discovery workflow started",
            }
        except Exception as exc:
            logger.warning("GCP Workflows call failed, falling back to local: %s", exc)

    # Fallback: use LocalWorkflowRunner or mock store
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
        "message": "Workflow queued (using local runner)",
    }


@router.post("/sample-qc")
async def start_sample_qc(params: SampleQCParams) -> dict:
    """Start a sample QC workflow."""
    workflow_id = f"sample-qc-{uuid.uuid4().hex[:12]}"

    if _is_gcp_available():
        try:
            from google.cloud.workflows.executions_v1 import ExecutionsClient
            from google.cloud.workflows.executions_v1.types import Execution

            from workflows.config import WorkflowConfig

            config = WorkflowConfig()
            client = ExecutionsClient()
            parent = (
                f"projects/{config.project}/locations/{config.location}"
                f"/workflows/{config.sample_qc_id}"
            )

            import json

            execution = client.create_execution(
                parent=parent,
                execution=Execution(
                    argument=json.dumps(
                        {
                            "dataset": params.dataset,
                            "classification_methods": params.classification_methods,
                            "n_iterations": params.n_iterations,
                            "activity_service_url": config.activity_service_url,
                            "workflow_id": workflow_id,
                        }
                    )
                ),
            )
            return {
                "workflow_id": workflow_id,
                "execution_name": execution.name,
                "status": WorkflowStatus.RUNNING,
                "message": "Sample QC workflow started",
            }
        except Exception as exc:
            logger.warning("GCP Workflows call failed, falling back to local: %s", exc)

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
        "message": "Workflow queued (using local runner)",
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

    # Try progress table
    try:
        from workflows.progress import get_progress

        progress = await get_progress(workflow_id)
        if progress:
            return progress
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


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

    # Try progress table
    try:
        from workflows.progress import get_progress

        progress = await get_progress(workflow_id)
        if progress and progress.get("status") == "completed":
            return {"workflow_id": workflow_id, "report": progress}
        if progress:
            return {
                "workflow_id": workflow_id,
                "status": progress["status"],
                "message": "Workflow has not completed yet",
            }
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
