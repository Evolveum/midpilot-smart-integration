# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from unittest.mock import patch

import pytest

from src.common.errors import LLMResponseValidationException
from src.common.schema import ApplicationSchema, BaseSchemaAttribute
from src.modules.extension_att.schema import (
    SuggestExtensionRequest,
    SuggestExtensionResponse,
)
from src.modules.extension_att.service import (
    _build_extension_prompt_data,
    suggest_extension,
)
from test.unit.modules.utils import response_mock


# ---- _build_extension_prompt_data tests ----
def _make_req(attrs: list[BaseSchemaAttribute]) -> SuggestExtensionRequest:
    app_schema = ApplicationSchema(name="ri:account", attribute=attrs)
    # Provide basic stats for each attribute (required by the schema)
    stats = {
        a.name: {
            "totalCount": 1000,
            "nuniq": 1000 if "personalNumber" in a.name else 12 if "department" in a.name else 980,
            "nmissing": 0 if "personalNumber" in a.name else 5 if "department" in a.name else 20,
        }
        for a in attrs
    }
    return SuggestExtensionRequest(applicationSchema=app_schema, attributeStats=stats)


def test_build_extension_prompt_data_basic():
    attrs = [
        BaseSchemaAttribute(
            name="c:attributes/ri:personalNumber",
            type="xsd:string",
            minOccurs=0,
            maxOccurs=1,
            description="Employee personal number.",
        ),
        BaseSchemaAttribute(
            name="c:attributes/ri:department",
            type="xsd:string",
            minOccurs=0,
            maxOccurs=1,
            description=None,
        ),
    ]
    req = _make_req(attrs)

    data = _build_extension_prompt_data(req)
    assert set(data.keys()) == {"Resource_schema", "Attribute_stats"}

    payload = json.loads(data["Resource_schema"])  # avoid whitespace sensitivity
    assert payload == {
        "c:attributes/ri:personalNumber": {
            "type": "xsd:string",
            "description": "Employee personal number.",
        },
        "c:attributes/ri:department": {
            "type": "xsd:string",
            "description": "",
        },
    }

    # Stats are required; ensure they are present and contain keys for provided attributes
    stats_payload = json.loads(data["Attribute_stats"])  # dict
    assert set(stats_payload.keys()) == {"c:attributes/ri:personalNumber", "c:attributes/ri:department"}


# ---- suggest_extension tests ----
@pytest.mark.asyncio
@patch(
    "src.modules.extension_att.service.get_default_llm",
    response_mock(
        '{"extensionAttributes": ["  c:attributes/ri:department  ", "c:attributes/ri:personalNumber", "c:attributes/ri:unknown", "", "c:attributes/ri:department"]}'
    ),
)
async def test_suggest_extension_filters_dedupes_and_preserves_order():
    attrs = [
        BaseSchemaAttribute(
            name="c:attributes/ri:personalNumber",
            type="xsd:string",
            minOccurs=0,
            maxOccurs=1,
        ),
        BaseSchemaAttribute(
            name="c:attributes/ri:department",
            type="xsd:string",
            minOccurs=0,
            maxOccurs=1,
        ),
        BaseSchemaAttribute(
            name="c:attributes/ri:lastLogin",
            type="xsd:dateTime",
            minOccurs=0,
            maxOccurs=1,
        ),
    ]
    req = _make_req(attrs)

    resp = await suggest_extension(req)
    assert resp == SuggestExtensionResponse(
        extensionAttributes=[
            "c:attributes/ri:department",
            "c:attributes/ri:personalNumber",
        ]
    )


@pytest.mark.asyncio
@patch(
    "src.modules.extension_att.service.get_default_llm",
    response_mock("not a json that parser expects"),
)
async def test_suggest_extension_parser_error():
    attrs = [
        BaseSchemaAttribute(
            name="c:attributes/ri:uid",
            type="xsd:string",
            minOccurs=0,
            maxOccurs=1,
        )
    ]
    req = _make_req(attrs)

    with pytest.raises(LLMResponseValidationException):
        await suggest_extension(req)
