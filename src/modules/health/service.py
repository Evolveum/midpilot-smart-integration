# Copyright (c) 2010-2026 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
from typing import List

from langchain_core.messages import HumanMessage

from ...common.langfuse import langfuse
from ...common.llm import get_default_llm
from ...common.schema import get_response_metadata
from ...config import config
from ...utils import get_version_info
from .schema import CheckResult, HealthResponse, HealthStatus

logger = logging.getLogger(__name__)


async def run_health_checks() -> HealthResponse:
    """
    Run all health checks and return the aggregated result.

    :return: HealthResponse with overall status and per-check results.
    """
    checks: List[CheckResult] = []

    checks.append(CheckResult(name="server", status=HealthStatus.OK))

    try:
        llm = get_default_llm()
        await llm.ainvoke([HumanMessage(content="Say hello")])
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
