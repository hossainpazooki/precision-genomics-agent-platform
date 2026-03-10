"""Workflow I/O schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from core.models import CustomBaseModel


class WorkflowStatus(StrEnum):
    """Lifecycle status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Biomarker Discovery
# ---------------------------------------------------------------------------


class BiomarkerDiscoveryParams(CustomBaseModel):
    """Input parameters for the biomarker discovery workflow."""

    dataset: str = "train"
    target: str = "msi"
    modalities: list[str] = ["proteomics", "rnaseq"]
    n_top_features: int = 30
    cv_folds: int = 10


class BiomarkerDiscoveryResult(CustomBaseModel):
    """Final output of the biomarker discovery workflow."""

    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None = None
    target: str
    modalities: list[str]
    feature_panel: dict = {}
    classification_metrics: dict = {}
    cross_omics_validation: dict = {}
    interpretation: dict = {}
    error: str | None = None


class BiomarkerDiscoveryProgress(CustomBaseModel):
    """Progress snapshot queryable during workflow execution."""

    workflow_id: str
    status: WorkflowStatus
    current_phase: str = "pending"
    phases_completed: list[str] = []
    phases_remaining: list[str] = []


# ---------------------------------------------------------------------------
# Sample QC
# ---------------------------------------------------------------------------


class SampleQCParams(CustomBaseModel):
    """Input parameters for the sample QC workflow."""

    dataset: str = "train"
    classification_methods: list[str] = ["ensemble"]
    distance_methods: list[str] = ["hungarian"]
    n_iterations: int = 100


class SampleQCResult(CustomBaseModel):
    """Final output of the sample QC workflow."""

    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None = None
    total_samples: int = 0
    flagged_samples: list[dict] = []
    concordance_report: dict = {}
    error: str | None = None


class SampleQCProgress(CustomBaseModel):
    """Progress snapshot for sample QC workflow."""

    workflow_id: str
    status: WorkflowStatus
    current_phase: str = "pending"
    samples_processed: int = 0
    total_samples: int = 0


# ---------------------------------------------------------------------------
# Generic Workflow Info
# ---------------------------------------------------------------------------


class WorkflowInfo(CustomBaseModel):
    """Metadata about a running or completed workflow."""

    workflow_id: str
    workflow_type: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: datetime | None = None
    run_id: str | None = None
    execution_name: str | None = None
