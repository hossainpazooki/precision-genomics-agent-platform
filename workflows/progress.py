"""Workflow execution progress tracking via Cloud SQL."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Column, Field, SQLModel

try:
    from sqlalchemy import JSON
except ImportError:
    JSON = None


class WorkflowExecution(SQLModel, table=True):
    """Tracks progress of a workflow execution."""

    __tablename__ = "workflow_executions"

    id: int | None = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True, unique=True)
    workflow_type: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    current_phase: str = Field(default="pending")
    phases_completed: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = Field(default=None)
    result: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    error: str | None = Field(default=None)


async def update_progress(
    workflow_id: str,
    *,
    status: str | None = None,
    current_phase: str | None = None,
    phase_completed: str | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    """Update progress for a workflow execution in the database."""
    from core.database import get_session

    async with get_session() as session:
        from sqlmodel import select

        stmt = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        execution = (await session.execute(stmt)).scalar_one_or_none()
        if not execution:
            return

        if status:
            execution.status = status
        if current_phase:
            execution.current_phase = current_phase
        if phase_completed and phase_completed not in execution.phases_completed:
            execution.phases_completed = [*execution.phases_completed, phase_completed]
        if result:
            execution.result = result
        if error:
            execution.error = error
        if status in ("completed", "failed"):
            execution.completed_at = datetime.now(UTC)

        session.add(execution)
        await session.commit()


async def get_progress(workflow_id: str) -> dict | None:
    """Get progress for a workflow execution."""
    from core.database import get_session

    async with get_session() as session:
        from sqlmodel import select

        stmt = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        execution = (await session.execute(stmt)).scalar_one_or_none()
        if not execution:
            return None

        return {
            "workflow_id": execution.workflow_id,
            "workflow_type": execution.workflow_type,
            "status": execution.status,
            "current_phase": execution.current_phase,
            "phases_completed": execution.phases_completed,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error": execution.error,
        }
