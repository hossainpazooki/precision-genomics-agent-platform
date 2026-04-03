"""MCP tool: Express an intent and begin its lifecycle."""

from __future__ import annotations

import logging

from mcp_server.schemas.intents import ExpressIntentInput, ExpressIntentOutput

logger = logging.getLogger(__name__)


async def run_tool(input_data: ExpressIntentInput) -> ExpressIntentOutput:
    """Create an intent and kick off the controller's process loop."""
    from intents.service import create_intent, get_controller, get_intent

    # Create the intent record.
    intent = await create_intent(
        intent_type=input_data.intent_type,
        params=input_data.params,
        requested_by="mcp",
    )

    # Drive it through whatever transitions are immediately possible.
    controller = get_controller()
    await controller.process(intent.intent_id)

    # Reload to get updated status.
    updated = await get_intent(intent.intent_id)
    status = updated["status"] if updated else intent.status

    return ExpressIntentOutput(
        intent_id=intent.intent_id,
        intent_type=intent.intent_type,
        status=status,
        message=f"Intent {intent.intent_id} created and processing started.",
    )
