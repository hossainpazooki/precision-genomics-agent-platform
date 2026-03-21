"""Typed configuration for the Precision Genomics infrastructure."""

from dataclasses import dataclass

import pulumi


@dataclass(frozen=True)
class InfraConfig:
    """Strongly-typed infrastructure configuration.

    Loaded from Pulumi stack config files (Pulumi.dev.yaml, etc.).
    Secrets are kept as pulumi.Output[str] to prevent accidental logging.
    """

    project_id: str
    region: str
    zone: str
    db_tier: str
    db_password: pulumi.Output[str]
    anthropic_api_key: pulumi.Output[str]
    experiment_name: str


def load_config() -> InfraConfig:
    """Load configuration from the active Pulumi stack."""
    cfg = pulumi.Config()
    gcp_cfg = pulumi.Config("gcp")

    return InfraConfig(
        project_id=gcp_cfg.require("project"),
        region=gcp_cfg.get("region") or "us-central1",
        zone=cfg.get("zone") or "us-central1-a",
        db_tier=cfg.get("db_tier") or "db-custom-2-8192",
        db_password=cfg.require_secret("db_password"),
        anthropic_api_key=cfg.require_secret("anthropic_api_key"),
        experiment_name=cfg.get("experiment_name") or "precision-genomics",
    )
