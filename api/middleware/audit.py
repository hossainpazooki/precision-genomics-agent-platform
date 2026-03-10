"""Audit logging middleware for request tracking."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = structlog.get_logger("audit")


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every request with timing and a unique request ID."""

    EXCLUDED_PATHS: set[str] = {"/health", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, enabled: bool = True) -> None:  # noqa: ANN001
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled or request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        logger.info(
            "request_start",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "request_end",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 1),
        )

        response.headers["X-Request-ID"] = request_id
        return response
