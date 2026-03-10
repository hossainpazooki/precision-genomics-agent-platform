"""Structured logging setup with structlog and optional Cloud Logging integration."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(environment: str = "local") -> None:
    """Configure structlog with appropriate renderer for the environment.

    - ``local``: Console renderer with colors for human readability.
    - ``production`` / other: JSON renderer for Cloud Logging ingestion.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "local":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()
        _setup_cloud_logging()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def _setup_cloud_logging() -> None:
    """Integrate with Google Cloud Logging if available."""
    try:
        import google.cloud.logging

        client = google.cloud.logging.Client()
        client.setup_logging()
    except ImportError:
        pass
    except Exception:
        logging.getLogger(__name__).debug("Cloud Logging setup failed; using stdout", exc_info=True)
