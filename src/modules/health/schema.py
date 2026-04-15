# Copyright (c) 2010-2026 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"


class CheckResult(BaseModel):
    name: str
    status: HealthStatus
    error: Optional[str] = Field(None)


class HealthResponse(BaseModel):
    status: HealthStatus
    checks: List[CheckResult]
