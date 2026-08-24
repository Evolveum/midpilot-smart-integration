# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .common.errors import ServiceUnavailableException
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
        """
        Log every incoming request and its response at DEBUG level.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Incoming request: %s %s",
                request.method,
                request.url,
            )

        try:
            response = await call_next(request)
        except Exception:
            logger.debug(
                "Request failed: %s %s",
                request.method,
                request.url,
                exc_info=True,
            )
            raise

        logger.debug(
            "Outgoing response: %s %s | status=%s",
            request.method,
            request.url,
            response.status_code,
        )

        return response

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
