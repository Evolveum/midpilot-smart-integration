# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from unittest.mock import patch

import pytest

from src.modules.categorical_mapping.schema import (
    AttributeValueCount,
    SuggestCategoricalMappingRequest,
    SuggestCategoricalMappingResponse,
)
from src.modules.categorical_mapping.service import (
    build_prompt_data,
    suggest_categorical_mapping_script,
)
from src.common.schema import BaseSchemaAttribute
from test.unit.modules.utils import response_mock

APP_ATTR = BaseSchemaAttribute(name="ri:status", type="xsd:string", minOccurs=0, maxOccurs=1)
MP_ATTR = BaseSchemaAttribute(
    name="c:activation/c:administrativeStatus", type="xsd:string", minOccurs=0, maxOccurs=1
)
MP_ENUM = ["enabled", "disabled", "archived"]


# ---- build_prompt_data tests (deterministic) ----


def test_build_prompt_data_sorted_by_count_descending():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValueCount=[
            AttributeValueCount(value="inactive", count=5),
            AttributeValueCount(value="active", count=100),
            AttributeValueCount(value="deleted", count=2),
        ],
        midPointCategoryValue=MP_ENUM,
    )
    data = build_prompt_data(req)
    lines = data["value_distribution"].splitlines()
    assert "'active': 100" in lines[0]
    assert "'inactive': 5" in lines[1]
    assert "'deleted': 2" in lines[2]


def test_build_prompt_data_mp_enum_values_quoted():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValueCount=[],
        midPointCategoryValue=["enabled", "disabled", "archived"],
    )
    data = build_prompt_data(req)
    assert data["mp_enum_values"] == '"enabled", "disabled", "archived"'


def test_build_prompt_data_empty_value_counts():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValueCount=[],
        midPointCategoryValue=MP_ENUM,
    )
    data = build_prompt_data(req)
    assert data["value_distribution"] == "  (none)"


def test_build_prompt_data_attribute_names():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValueCount=[AttributeValueCount(value="1", count=10)],
        midPointCategoryValue=MP_ENUM,
    )
    data = build_prompt_data(req)
    assert data["app_attr_name"] == "ri:status"
    assert data["app_attr_type"] == "xsd:string"
    assert data["mp_attr_name"] == "c:activation/c:administrativeStatus"


def test_build_prompt_data_lockout_status():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=BaseSchemaAttribute(
            name="ri:lockout", type="xsd:string", minOccurs=0, maxOccurs=1
        ),
        midPointAttribute=BaseSchemaAttribute(
            name="c:activation/c:lockoutStatus", type="xsd:string", minOccurs=0, maxOccurs=1
        ),
        inbound=True,
        applicationAttributeValueCount=[
            AttributeValueCount(value="0", count=980),
            AttributeValueCount(value="1", count=20),
        ],
        midPointCategoryValue=["normal", "locked"],
    )
    data = build_prompt_data(req)
    assert data["mp_enum_values"] == '"normal", "locked"'
    lines = data["value_distribution"].splitlines()
    assert "'0': 980" in lines[0]
    assert "'1': 20" in lines[1]


# ---- suggest_categorical_mapping_script tests ----


@pytest.mark.asyncio
@patch(
    "src.modules.categorical_mapping.service.get_default_llm",
    response_mock(
        '{"description":"Map status to administrativeStatus","transformationScript":"// Map status to administrativeStatus\\nif (input == null) return null\\ninput.equalsIgnoreCase(\\"active\\") ? \\"enabled\\" : input.equalsIgnoreCase(\\"inactive\\") ? \\"disabled\\" : null"}'
    ),
)
async def test_suggest_categorical_mapping_script_basic(monkeypatch):
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValueCount=[
            AttributeValueCount(value="active", count=100),
            AttributeValueCount(value="inactive", count=50),
        ],
        midPointCategoryValue=MP_ENUM,
    )
    resp = await suggest_categorical_mapping_script(req)
    assert isinstance(resp, SuggestCategoricalMappingResponse)
    assert resp.description == "Map status to administrativeStatus"
    assert resp.transformationScript is not None
    assert resp.transformationScript.startswith("// Map status to administrativeStatus")


@pytest.mark.asyncio
@patch(
    "src.modules.categorical_mapping.service.get_default_llm",
    response_mock(
        '{"description":"Map lockout flag to lockoutStatus","transformationScript":"// Map lockout flag to lockoutStatus\\ninput == null ? null : (input.equalsIgnoreCase(\\"1\\") ? \\"locked\\" : \\"normal\\")"}'
    ),
)
async def test_suggest_categorical_mapping_script_lockout(monkeypatch):
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=BaseSchemaAttribute(
            name="ri:lockout", type="xsd:string", minOccurs=0, maxOccurs=1
        ),
        midPointAttribute=BaseSchemaAttribute(
            name="c:activation/c:lockoutStatus", type="xsd:string", minOccurs=0, maxOccurs=1
        ),
        inbound=True,
        applicationAttributeValueCount=[
            AttributeValueCount(value="0", count=980),
            AttributeValueCount(value="1", count=20),
        ],
        midPointCategoryValue=["normal", "locked"],
    )
    resp = await suggest_categorical_mapping_script(req)
    assert resp.description == "Map lockout flag to lockoutStatus"
    assert resp.transformationScript is not None
    first_line = resp.transformationScript.splitlines()[0]
    assert first_line == f"// {resp.description}"


@pytest.mark.asyncio
@patch(
    "src.modules.categorical_mapping.service.get_default_llm",
    response_mock('{"description":"Unresolvable mapping","transformationScript":null}'),
)
async def test_suggest_categorical_mapping_script_null_script(monkeypatch):
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValueCount=[],
        midPointCategoryValue=MP_ENUM,
    )
    resp = await suggest_categorical_mapping_script(req)
    assert resp.transformationScript is None
