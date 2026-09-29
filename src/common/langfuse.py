# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
import os
import ssl
from typing import Callable

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler

from ..config import config

"""Langfuse integration functions, used for development and testing purposes"""


def _configure_langfuse_otlp_certificate() -> None:
    ca_cert_file = config.langfuse.ca_cert_file
    if not ca_cert_file:
        return

    os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE", ca_cert_file)


def _build_langfuse_httpx_client() -> httpx.Client | None:
    ca_cert_file = config.langfuse.ca_cert_file
    if not ca_cert_file:
        return None

    return httpx.Client(verify=ssl.create_default_context(cafile=ca_cert_file))


_configure_langfuse_otlp_certificate()
langfuse_httpx_client = _build_langfuse_httpx_client()

# https://langfuse.com/docs/observability/sdk/python/setup
langfuse = Langfuse(
    host=config.langfuse.host,
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    httpx_client=langfuse_httpx_client,
    tracing_enabled=config.langfuse.tracing_enabled,
    environment=config.langfuse.environment,
)

# langfuse langchain handler that automatically observes runnables (chains)
langfuse_handler = CallbackHandler(public_key=config.langfuse.public_key)


class ObservedRoute(APIRoute):
    """
    Custom API route that starts new langfuse trace and automatically observes request and response.
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request_json = await request.json()
            with langfuse.start_as_current_observation(name="api_request", input=request_json) as span:
                with propagate_attributes(trace_name=request.url.path, tags=["smart_integration"]):
                    response: Response = await original_route_handler(request)
                    response_json = json.loads(bytes(response.body))
                    span.update(output=response_json)
                    return response

        return custom_route_handler


def ObservableAPIRouter():
    """
    Custom API router that automtatically start observing every route with langfuse.
    """

    return APIRouter(route_class=ObservedRoute)
