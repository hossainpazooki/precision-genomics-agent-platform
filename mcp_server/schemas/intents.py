"""Pydantic v2 I/O models for intent MCP tools."""

from __future__ import annotations

from typing import Any

from core.models import CustomBaseModel


# ---------------------------------------------------------------------------
# express_intent
# ---------------------------------------------------------------------------


class ExpressIntentInput(CustomBaseModel):
    """Input for expressing a new intent."""

    intent_type: str  # analysis | training | validation
    params: dict[str, Any] = {}
    # analysis params: dataset, target, modalities, n_top_features, analysis_type
    # training params: model_type (encoder|slm|cuml), dataset_uri, num_gpus, training_config
    # validation params: dataset, validation_type


class ExpressIntentOutput(CustomBaseModel):
    """Output from expressing an intent."""

    intent_id: str
    intent_type: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# get_intent_status
# ---------------------------------------------------------------------------


class GetIntentStatusInput(CustomBaseModel):
    """Input for checking intent status."""

    intent_id: str


class GetIntentStatusOutput(CustomBaseModel):
    """Output from checking intent status."""

    intent_id: str
    intent_type: str
    status: str
    workflow_ids: list[str] = []
    eval_results: dict[str, Any] = {}
    infra_state: dict[str, Any] = {}
    created_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
