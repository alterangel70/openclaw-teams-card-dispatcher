"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.dispatch import router as dispatch_router
from app.api.routes.health import router as health_router
from app.config import get_settings
from app.logging import configure_logging

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to each request and response."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        return response


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name)
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(health_router)
    app.include_router(dispatch_router)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("API startup complete", extra={"correlation_id": "system"})

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("API shutdown complete", extra={"correlation_id": "system"})

    return app


app = create_app()
