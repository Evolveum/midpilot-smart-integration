# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
from typing import Any

from fastapi import HTTPException

LOGGER = logging.getLogger(__name__)

class ServiceUnavailableException(HTTPException):
    """
    Exception raised when the service or one of its dependencies is unavailable.
    """

    def __init__(self, detail: Any = "Service Unavailable"):
        super().__init__(status_code=503, detail=detail)


class LLMResponseValidationException(HTTPException):
    """
    Exception raised when an LLM response fails validation.
    """

    def __init__(self):
        super().__init__(status_code=550, detail="LLM Response Validation Error")


class LLMTimeoutException(HTTPException):
    """
    Exception raised when an LLM request exceeds the configured timeout.
    """

    def __init__(self, timeout: int):
        LOGGER.debug("LLM request timed out after %s seconds", timeout)
        super().__init__(
            status_code=504,
            detail=f"LLM request timed out after {timeout} seconds",
        )


class NotImplementedError(HTTPException):
    """
    Exception raised for functionality not being implemented yet.
    """

    def __init__(self):
        super().__init__(status_code=501, detail="Not Implemented")



class InvalidValueException(HTTPException):
    """
    Exception raised when an input value does not conform to the expected schema.
    """

    def __init__(self, detail: Any):
        LOGGER.debug("Invalid value: %s", detail)
        super().__init__(status_code=400, detail=detail)
