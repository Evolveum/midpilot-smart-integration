# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import Any
from unittest.mock import Mock

from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel


class ResponseMock(str):
    @property
    def content(self) -> str:
        return str(self)


def response_mock(content: Any) -> Mock:
    """
    Returns a Mock that yields a RunnableLambda which returns either:
      * the provided BaseModel (if one was given), or
      * a string-like object with a `.content` property.
    """

    def _runner(*args, **kwargs):
        if isinstance(content, BaseModel):
            return content
        return ResponseMock(str(content))

    return Mock(return_value=RunnableLambda(lambda *a, **k: _runner(*a, **k)))
