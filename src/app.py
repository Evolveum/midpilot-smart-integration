# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .common.errors import ServiceUnavailableException
from .common.logger import request_id
from .config import config
from .modules.health.schema import HealthResponse, HealthStatus
from .modules.health.service import run_health_checks
from .router import root_router
from .utils import get_version_info

logger = logging.getLogger(__name__)


def create_api() -> FastAPI:
    """
    Initialize and configure the FastAPI application.

    :return: Configured FastAPI instance.
    """
    app = FastAPI(title=config.app.title, version=get_version_info(), root_path=config.app.root_path)
    app.include_router(root_router, prefix=config.app.api_base_url)

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        """Log request outcomes and correlate application logs without logging payloads."""
        token = request_id.set(uuid4().hex)
        started = perf_counter()
        try:
            logger.debug("Request started: method=%s path=%s", request.method, request.url.path)
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id.get()
            level = logging.INFO
            if response.status_code >= 500:
                level = logging.ERROR
            elif response.status_code >= 400:
                level = logging.WARNING
            elif request.scope.get("route") and request.scope["route"].path == "/health":
                level = logging.DEBUG
            logger.log(
                level,
                "Request completed: method=%s path=%s status=%s duration_ms=%.1f",
                request.method,
                request.url.path,
                response.status_code,
                (perf_counter() - started) * 1000,
            )
            return response
        except Exception as exc:
            logger.error(
                "Request failed: method=%s path=%s status=500 duration_ms=%.1f error_type=%s",
                request.method,
                request.url.path,
                (perf_counter() - started) * 1000,
                type(exc).__name__,
            )
            raise
        finally:
            request_id.reset(token)

    @app.exception_handler(ServiceUnavailableException)
    async def service_unavailable_handler(request: Request, exc: ServiceUnavailableException) -> JSONResponse:
        return JSONResponse(content=exc.detail, status_code=exc.status_code)

    @app.get("/health")
    async def health() -> HealthResponse:
        """
        Health check endpoint.
        Responds with "Service Unavailable" when unhealthy.
        """
        result = await run_health_checks()
        if result.status != HealthStatus.OK:
            raise ServiceUnavailableException(result.model_dump())
        return result

    return app


api = create_api()
