"""FastAPI application factory for the Precision Genomics Agent Platform."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    get_settings()
    yield
    from core.database import reset_engine

    reset_engine()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Audit middleware
    from api.middleware.audit import AuditMiddleware

    app.add_middleware(AuditMiddleware, enabled=True)

    # Auth middleware
    from api.middleware.auth import OptionalAuthMiddleware

    app.add_middleware(OptionalAuthMiddleware)

    # Include routers
    from api.routes.analysis import router as analysis_router
    from api.routes.biomarkers import router as biomarkers_router
    from api.routes.workflows import router as workflows_router

    app.include_router(analysis_router)
    app.include_router(biomarkers_router)
    app.include_router(workflows_router)

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    @app.get("/", tags=["Health"])
    async def root() -> dict:
        """Root endpoint."""
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


app = create_app()
