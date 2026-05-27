# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .common.errors import ServiceUnavailableException
from .config import config
from .modules.health.schema import HealthResponse, HealthStatus
from .modules.health.service import run_health_checks
from .router import root_router
from .utils import get_version_info

logger = logging.getLogger(__name__)


class TimeoutMiddleware:
    """
    ASGI middleware that enforces a maximum processing time per request.

    If the request exceeds the configured timeout, a 504 Gateway Timeout response is returned
    and the downstream task (including any in-flight LLM HTTP call) is cancelled.

    Timeout is configured via APP__REQUEST_TIMEOUT environment variable.
    """

    def __init__(self, app: ASGIApp, timeout: int) -> None:
        self.app = app
        self.timeout = timeout

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            with anyio.fail_after(self.timeout):
                await self.app(scope, receive, send_wrapper)
        except TimeoutError:
            if response_started:
                # Response already in flight; cannot send a 504 anymore.
                logger.warning("Request exceeded timeout after response had started; downstream cancelled.")
                return
            response = JSONResponse({"detail": "Request timeout"}, status_code=504)
            await response(scope, receive, send)


def create_api() -> FastAPI:
    """
    Initialize and configure the FastAPI application.

    :return: Configured FastAPI instance.
    """
    app = FastAPI(title=config.app.title, version=get_version_info(), root_path=config.app.root_path)
    app.add_middleware(TimeoutMiddleware, timeout=config.app.request_timeout)
    app.include_router(root_router, prefix=config.app.api_base_url)

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
