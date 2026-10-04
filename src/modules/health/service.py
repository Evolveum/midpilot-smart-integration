# Copyright (c) 2010-2026 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
import ssl
from typing import List

import httpx2
import openai

from ...common.langfuse import langfuse
from ...common.llm import invoke_with_auth_guard
from ...common.schema import get_response_metadata
from ...config import config
from ...utils import get_version_info
from .schema import CheckResult, HealthResponse, HealthStatus

logger = logging.getLogger(__name__)


async def check_llm() -> None:
    verify: ssl.SSLContext | bool = (
        ssl.create_default_context(cafile=config.llm.ca_cert_file) if config.llm.ca_cert_file else True
    )
    async with openai.AsyncOpenAI(
        api_key=config.llm.openai_api_key,
        base_url=config.llm.openai_api_base,
        http_client=httpx2.AsyncClient(verify=verify),
        timeout=5,
        max_retries=0,
    ) as client:
        models = await invoke_with_auth_guard(client.models.list())

    if config.llm.model_name not in {model.id for model in models.data}:
        raise ValueError(f"Model '{config.llm.model_name}' is not available")


async def run_health_checks() -> HealthResponse:
    """
    Run all health checks and return the aggregated result.

    :return: HealthResponse with overall status and per-check results.
    """
    checks: List[CheckResult] = []

    checks.append(CheckResult(name="server", status=HealthStatus.OK))

    try:
        await check_llm()
        checks.append(CheckResult(name="llm", status=HealthStatus.OK))
    except Exception as e:
        logger.error("LLM health check failed: %s", e, exc_info=True)
        checks.append(CheckResult(name="llm", status=HealthStatus.ERROR, error=str(e)))

    if config.langfuse.tracing_enabled:
        try:
            langfuse.auth_check()
            checks.append(CheckResult(name="langfuse", status=HealthStatus.OK))
        except Exception as e:
            logger.error("Langfuse health check failed: %s", e, exc_info=True)
            checks.append(CheckResult(name="langfuse", status=HealthStatus.ERROR, error=str(e)))
    else:
        checks.append(CheckResult(name="langfuse", status=HealthStatus.DISABLED))

    overall = HealthStatus.OK if all(c.status != HealthStatus.ERROR for c in checks) else HealthStatus.ERROR
    return HealthResponse(status=overall, version=get_version_info(), metadata=get_response_metadata(), checks=checks)
