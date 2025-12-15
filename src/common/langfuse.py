# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from ..config import config

"""Langfuse integration functions, used for development and testing purposes"""

# https://langfuse.com/docs/observability/sdk/python/setup
langfuse = Langfuse(
    host=config.langfuse.host,
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
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
            with langfuse.start_as_current_span(name="api_request", input=request_json) as span:
                span.update_trace(name=request.url.path, tags=["smart_integration"])
                response: Response = await original_route_handler(request)
                response_json = json.loads(response.body)
                span.update(output=response_json)
                return response

        return custom_route_handler


def ObservableAPIRouter():
    """
    Custom API router that automtatically start observing every route with langfuse.
    """

    return APIRouter(route_class=ObservedRoute)
