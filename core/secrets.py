"""GCP Secret Manager integration for loading secrets at startup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Settings

logger = logging.getLogger(__name__)

# Mapping: secret name in GCP -> Settings field name
_SECRET_MAP = {
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "DATABASE_URL": "database_url",
    "REDIS_URL": "redis_url",
}


def _access_secret(client, project_id: str, secret_id: str) -> str | None:  # noqa: ANN001
    """Access the latest version of a secret from GCP Secret Manager."""
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception:
        logger.debug("Secret %s not found or inaccessible", secret_id)
        return None


def populate_secrets(settings: Settings) -> None:
    """Populate settings fields from GCP Secret Manager.

    Only overwrites fields that are unset (None or default) and have
    a corresponding secret in Secret Manager. No-op if the
    google-cloud-secret-manager package is not installed.
    """
    try:
        from google.cloud.secretmanager import SecretManagerServiceClient
    except ImportError:
        logger.warning("google-cloud-secret-manager not installed; skipping secret loading")
        return

    client = SecretManagerServiceClient()
    project_id = settings.gcp_project_id

    for secret_name, field_name in _SECRET_MAP.items():
        current = getattr(settings, field_name, None)
        # Only fetch if the field is unset or still at its default
        if current is None or (field_name == "database_url" and "localhost" in current):
            value = _access_secret(client, project_id, secret_name)
            if value is not None:
                object.__setattr__(settings, field_name, value)
                logger.info("Loaded secret %s from Secret Manager", secret_name)
