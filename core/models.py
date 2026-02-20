"""Shared base model and SQLModel ORM models for the platform."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlmodel import Column, Field, SQLModel

try:
    from sqlalchemy import JSON
except ImportError:
    JSON = None


class CustomBaseModel(BaseModel):
    """Base model with consistent serialization defaults."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() + "Z"},
    )


# ---------------------------------------------------------------------------
# ORM Table Models
# ---------------------------------------------------------------------------


class AnalysisRun(SQLModel, table=True):
    """Tracks a single analysis pipeline execution."""

    __tablename__ = "analysis_runs"

    id: int | None = Field(default=None, primary_key=True)
    status: str = Field(default="pending", index=True)
    target: str = Field(description="msi | gender | mismatch")
    modality: str = Field(description="proteomics | rnaseq | combined")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = Field(default=None)
    config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    results: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class BiomarkerPanel(SQLModel, table=True):
    """A discovered set of biomarker features from an analysis run."""

    __tablename__ = "biomarker_panels"

    id: int | None = Field(default=None, primary_key=True)
    analysis_run_id: int = Field(index=True)
    target: str
    modality: str
    features: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    method_agreement: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SampleQCResult(SQLModel, table=True):
    """QC result for a single sample (mismatch detection)."""

    __tablename__ = "sample_qc_results"

    id: int | None = Field(default=None, primary_key=True)
    analysis_run_id: int = Field(index=True)
    sample_id: str = Field(index=True)
    flagged_by_classification: bool = Field(default=False)
    flagged_by_distance_matrix: bool = Field(default=False)
    concordance_level: str = Field(default="none", description="none | single | high")
    confidence: float = Field(default=0.0)
    details: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class FeatureSnapshot(SQLModel, table=True):
    """Time-series snapshot of a feature value (TimescaleDB hypertable candidate)."""

    __tablename__ = "feature_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    panel_id: int = Field(index=True)
    feature_name: str = Field(index=True)
    value: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    source: str = Field(default="pipeline")
    confidence: float = Field(default=1.0)
