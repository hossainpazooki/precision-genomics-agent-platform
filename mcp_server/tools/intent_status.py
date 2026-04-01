"""MCP tool: Check the status of an existing intent."""

from __future__ import annotations

import logging

from mcp_server.schemas.intents import GetIntentStatusInput, GetIntentStatusOutput

logger = logging.getLogger(__name__)


async def run_tool(input_data: GetIntentStatusInput) -> GetIntentStatusOutput:
    """Look up an intent by ID and return its current state."""
    from intents.service import get_intent

    intent = await get_intent(input_data.intent_id)
    if intent is None:
        return GetIntentStatusOutput(
            intent_id=input_data.intent_id,
            intent_type="unknown",
            status="not_found",
            error=f"Intent {input_data.intent_id} not found",
        )

    return GetIntentStatusOutput(
        intent_id=intent["intent_id"],
        intent_type=intent["intent_type"],
        status=intent["status"],
        workflow_ids=intent.get("workflow_ids", []),
        eval_results=intent.get("eval_results", {}),
        infra_state=intent.get("infra_state", {}),
        created_at=intent.get("created_at"),
        completed_at=intent.get("completed_at"),
        error=intent.get("error"),
    )
