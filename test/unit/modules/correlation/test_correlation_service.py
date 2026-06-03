# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from unittest.mock import patch

import pytest

from src.common.errors import LLMResponseValidationException
from src.modules.correlation.schema import (
    BasicAttributeStats,
    SuggestExtensionCorrelatorsRequest,
)
from src.modules.correlation.service import suggest_extension_correlators
from test.unit.modules.utils import response_mock

# Common request payload used across tests
_req = SuggestExtensionCorrelatorsRequest(
    schemaName="c:UserType",
    schemaDescription="User object type with HR-driven extensions",
    extensionAttributes=[
        {
            "name": "c:extension/ext:personalNumber",
            "type": "xsd:string",
            "description": "Unique personal number assigned by HR.",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        {
            "name": "c:extension/ext:email",
            "type": "xsd:string",
            "description": "Corporate email address.",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        {
            "name": "c:extension/ext:phone",
            "type": "xsd:string",
            "description": "Mobile or office phone number.",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
    ],
    attributeStats={
        "c:extension/ext:personalNumber": BasicAttributeStats(totalCount=1000, nuniq=995, nmissing=5),
        "c:extension/ext:email": BasicAttributeStats(totalCount=1000, nuniq=980, nmissing=20),
        "c:extension/ext:phone": BasicAttributeStats(totalCount=1000, nuniq=850, nmissing=150),
    },
)


@pytest.mark.asyncio
@patch(
    "src.modules.correlation.service.get_default_llm",
    response_mock(
        json.dumps(
            {
                "correlators": [
                    "c:extension/ext:personalNumber",
                    "c:extension/ext:email",
                ]
            }
        )
    ),
)
async def test_returns_correlators_list():
    resp = await suggest_extension_correlators(_req)
    assert resp.correlators == [
        "c:extension/ext:personalNumber",
        "c:extension/ext:email",
    ]


@pytest.mark.asyncio
@patch(
    "src.modules.correlation.service.get_default_llm",
    response_mock(json.dumps({"correlators": []})),
)
async def test_allows_empty_list():
    resp = await suggest_extension_correlators(_req)
    assert resp.correlators == []


@pytest.mark.asyncio
@patch("src.modules.correlation.service.get_default_llm", response_mock("{ invalid: json }"))
async def test_invalid_json_raises():
    with pytest.raises(LLMResponseValidationException):
        await suggest_extension_correlators(_req)
