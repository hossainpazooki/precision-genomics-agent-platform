"""Database connection management for PostgreSQL + TimescaleDB."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import MetaData, text
from sqlmodel import Session, SQLModel, create_engine

from core.config import get_settings

if TYPE_CHECKING:
    from collections.abc import Generator

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
SQLModel.metadata.naming_convention = convention

_engine = None


def _normalize_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy compatibility."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def get_engine():
    """Get SQLAlchemy engine with connection pooling (lazy singleton)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url = _normalize_url(settings.database_url)
        _engine = create_engine(
            database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def reset_engine() -> None:
    """Reset the engine singleton (for testing or shutdown)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel session for FastAPI dependency injection."""
    with Session(get_engine()) as session:
        yield session


def init_timescaledb_hypertable(table_name: str, time_column: str = "ts") -> None:
    """Initialize a TimescaleDB hypertable for time-series data.

    Safe to call multiple times; skips if already a hypertable or if
    TimescaleDB is not installed.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (  SELECT FROM information_schema.tables  WHERE table_name = :table_name)"),
                {"table_name": table_name},
            )
            if not result.scalar():
                return

            result = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT FROM timescaledb_information.hypertables"
                    "  WHERE hypertable_name = :table_name"
                    ")"
                ),
                {"table_name": table_name},
            )
            if result.scalar():
                return

            conn.execute(
                text(
                    "SELECT create_hypertable(:table_name, :time_column, if_not_exists => TRUE, migrate_data => TRUE)"
                ),
                {"table_name": table_name, "time_column": time_column},
            )
            conn.commit()
    except Exception:
        pass
