"""Feature store service for time-series feature snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from core.models import FeatureSnapshot


class FeatureStoreService:
    """Store and retrieve feature snapshots backed by FeatureSnapshot ORM model."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def store_snapshot(
        self,
        panel_id: int,
        feature_name: str,
        value: dict,
        source: str = "pipeline",
        confidence: float = 1.0,
    ) -> FeatureSnapshot:
        """Persist a new feature snapshot."""
        snapshot = FeatureSnapshot(
            panel_id=panel_id,
            feature_name=feature_name,
            value=value,
            ts=datetime.now(UTC),
            source=source,
            confidence=confidence,
        )
        self.session.add(snapshot)
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def get_latest(self, panel_id: int, feature_name: str) -> FeatureSnapshot | None:
        """Return the most recent snapshot for a given panel + feature."""
        statement = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.panel_id == panel_id)
            .where(FeatureSnapshot.feature_name == feature_name)
            .order_by(FeatureSnapshot.ts.desc())  # type: ignore[union-attr]
            .limit(1)
        )
        return self.session.exec(statement).first()

    def get_history(
        self,
        panel_id: int,
        feature_name: str,
        limit: int = 100,
    ) -> list[FeatureSnapshot]:
        """Return time-ordered history of snapshots for a panel + feature."""
        statement = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.panel_id == panel_id)
            .where(FeatureSnapshot.feature_name == feature_name)
            .order_by(FeatureSnapshot.ts.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return list(self.session.exec(statement).all())
