"""Optional API key authentication middleware."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

from core.config import get_settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

API_KEY_HEADER = "X-API-Key"


class OptionalAuthMiddleware:
    """ASGI middleware that validates API keys when REQUIRE_AUTH is enabled."""

    SKIP_PATHS: set[str] = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        if path in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        if not settings.require_auth:
            await self.app(scope, receive, send)
            return

        api_key = request.headers.get(API_KEY_HEADER)
        if not api_key:
            response = _json_response(
                {"detail": "Missing API key"}, status_code=401
            )
            await response(scope, receive, send)
            return

        valid_keys = _parse_api_keys(settings.api_keys)
        if api_key not in valid_keys:
            response = _json_response(
                {"detail": "Invalid API key"}, status_code=403
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _parse_api_keys(api_keys: str | None) -> set[str]:
    """Parse comma-separated API keys from settings."""
    if not api_keys:
        return set()
    return {k.strip() for k in api_keys.split(",") if k.strip()}


def _json_response(body: dict, status_code: int = 200) -> Response:
    """Create a JSON response."""
    return Response(
        content=json.dumps(body),
        status_code=status_code,
        media_type="application/json",
    )
