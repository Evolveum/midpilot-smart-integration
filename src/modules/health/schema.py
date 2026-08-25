# Copyright (c) 2010-2026 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from ...common.schema import ResponseMetadata, get_response_metadata


class HealthStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


class CheckResult(BaseModel):
    name: str
    status: HealthStatus
    error: Optional[str] = Field(None)


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str
    metadata: ResponseMetadata = Field(
        default_factory=get_response_metadata,
        description="Metadata about configured provider and used model.",
    )
    checks: List[CheckResult]
