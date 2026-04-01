"""SQLModel tables and persistence functions for intent lifecycle.

Follows the exact patterns from workflows/progress.py:
- SQLModel table with JSON columns for flexible state
- Async persistence functions using core.database.get_session
- Append-only event table for audit trail
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Column, Field, SQLModel

try:
    from sqlalchemy import JSON
except ImportError:
    JSON = None


# ---------------------------------------------------------------------------
# ORM Table: Intent
# ---------------------------------------------------------------------------


class Intent(SQLModel, table=True):
    """Tracks the lifecycle of a single intent."""

    __tablename__ = "intents"

    id: int | None = Field(default=None, primary_key=True)
    intent_id: str = Field(index=True, unique=True)
    intent_type: str = Field(index=True)  # analysis | training | validation
    status: str = Field(default="declared", index=True)

    # What was requested.
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Infrastructure resolution state (stack_name, worker_scaled, gcs_staged, …).
    infra_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Child workflow IDs (foreign keys into workflow_executions.workflow_id).
    workflow_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Eval assurance results ({eval_name: {score, passed, threshold, details}}).
    eval_results: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Lifecycle timestamps.
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = Field(default=None)
    activated_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    error: str | None = Field(default=None)
    requested_by: str = Field(default="agent")  # agent | api | mcp


# ---------------------------------------------------------------------------
# ORM Table: IntentEvent (append-only audit trail)
# ---------------------------------------------------------------------------


class IntentEvent(SQLModel, table=True):
    """Immutable record of an event in an intent's lifecycle."""

    __tablename__ = "intent_events"

    id: int | None = Field(default=None, primary_key=True)
    intent_id: str = Field(index=True)
    event_type: str = Field(index=True)  # state_change | workflow_started | eval_completed | infra_update | error
    from_status: str | None = Field(default=None)
    to_status: str | None = Field(default=None)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


# ---------------------------------------------------------------------------
# Persistence functions (async, matching workflows/progress.py)
# ---------------------------------------------------------------------------


async def update_intent(
    intent_id: str,
    *,
    status: str | None = None,
    infra_state: dict | None = None,
    workflow_ids: list[str] | None = None,
    eval_results: dict | None = None,
    error: str | None = None,
) -> None:
    """Update an intent record in the database."""
    from core.database import get_session

    async with get_session() as session:
        from sqlmodel import select

        stmt = select(Intent).where(Intent.intent_id == intent_id)
        intent = (await session.execute(stmt)).scalar_one_or_none()
        if not intent:
            return

        old_status = intent.status

        if status:
            intent.status = status
        if infra_state:
            intent.infra_state = {**intent.infra_state, **infra_state}
        if workflow_ids:
            intent.workflow_ids = list({*intent.workflow_ids, *workflow_ids})
        if eval_results:
            intent.eval_results = {**intent.eval_results, **eval_results}
        if error:
            intent.error = error

        # Lifecycle timestamps.
        now = datetime.now(UTC)
        if status == "resolving" and intent.resolved_at is None:
            intent.resolved_at = now
        if status == "active" and intent.activated_at is None:
            intent.activated_at = now
        if status in ("achieved", "failed", "cancelled"):
            intent.completed_at = now

        session.add(intent)

        # Emit state-change event if status changed.
        if status and status != old_status:
            event = IntentEvent(
                intent_id=intent_id,
                event_type="state_change",
                from_status=old_status,
                to_status=status,
            )
            session.add(event)

        await session.commit()


async def emit_event(
    intent_id: str,
    event_type: str,
    payload: dict | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
) -> None:
    """Append an event to the intent audit trail."""
    from core.database import get_session

    async with get_session() as session:
        event = IntentEvent(
            intent_id=intent_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            payload=payload or {},
        )
        session.add(event)
        await session.commit()


async def get_intent_record(intent_id: str) -> dict | None:
    """Load an intent as a plain dict (for API / MCP responses)."""
    from core.database import get_session

    async with get_session() as session:
        from sqlmodel import select

        stmt = select(Intent).where(Intent.intent_id == intent_id)
        intent = (await session.execute(stmt)).scalar_one_or_none()
        if not intent:
            return None

        return {
            "intent_id": intent.intent_id,
            "intent_type": intent.intent_type,
            "status": intent.status,
            "params": intent.params,
            "infra_state": intent.infra_state,
            "workflow_ids": intent.workflow_ids,
            "eval_results": intent.eval_results,
            "created_at": intent.created_at.isoformat(),
            "resolved_at": intent.resolved_at.isoformat() if intent.resolved_at else None,
            "activated_at": intent.activated_at.isoformat() if intent.activated_at else None,
            "completed_at": intent.completed_at.isoformat() if intent.completed_at else None,
            "error": intent.error,
            "requested_by": intent.requested_by,
        }
