"""GCP Workflows configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkflowConfig(BaseSettings):
    """Settings for GCP Workflows connection."""

    model_config = SettingsConfigDict(env_prefix="WORKFLOWS_", extra="ignore")

    project: str | None = None
    location: str = "us-central1"
    activity_service_url: str = "http://localhost:8081"

    biomarker_discovery_id: str = "precision-genomics-biomarker-discovery"
    sample_qc_id: str = "precision-genomics-sample-qc"
    prompt_optimization_id: str = "precision-genomics-prompt-optimization"
