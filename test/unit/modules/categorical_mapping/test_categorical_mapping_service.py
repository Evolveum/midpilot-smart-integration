# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from unittest.mock import patch

import pytest

from src.common.schema import BaseSchemaAttribute
from src.modules.categorical_mapping.prompts import suggest_categorical_mapping_system_prompt
from src.modules.categorical_mapping.schema import (
    SuggestCategoricalMappingRequest,
    SuggestCategoricalMappingResponse,
)
from src.modules.categorical_mapping.service import (
    build_prompt_data,
    suggest_categorical_mapping_script,
)
from test.unit.modules.utils import response_mock

APP_ATTR = BaseSchemaAttribute(name="ri:status", type="xsd:string", minOccurs=0, maxOccurs=1)
MP_ATTR = BaseSchemaAttribute(name="c:activation/c:administrativeStatus", type="xsd:string", minOccurs=0, maxOccurs=1)
MP_ENUM = ["enabled", "disabled", "archived"]


# ---- build_prompt_data tests (deterministic) ----


def test_categorical_prompt_uses_current_map_lookup_syntax():
    prompt = suggest_categorical_mapping_system_prompt
    assert "}}[input]" in prompt
    assert "Always" in prompt and "[input]" in prompt
    assert "Do not use optional map lookup `[?input]`" in prompt
    assert "Never use `[?input]`" in prompt
    assert "}}[?input]" not in prompt
    assert "that means `[?input]`" not in prompt
    assert "used literally in the `[?]`" not in prompt


def test_build_prompt_data_app_enum_values():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValue=["active", "inactive", "deleted"],
        midPointCategoryValue=MP_ENUM,
    )
    data = build_prompt_data(req)
    lines = data["app_enum_values"].splitlines()
    assert "'active'" in lines[0]
    assert "'inactive'" in lines[1]
    assert "'deleted'" in lines[2]


def test_build_prompt_data_mp_enum_values_quoted():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValue=[],
        midPointCategoryValue=["enabled", "disabled", "archived"],
    )
    data = build_prompt_data(req)
    assert data["mp_enum_values"] == '"enabled", "disabled", "archived"'


def test_build_prompt_data_empty_app_enum_values():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValue=[],
        midPointCategoryValue=MP_ENUM,
    )
    data = build_prompt_data(req)
    assert data["app_enum_values"] == "  (none)"


def test_build_prompt_data_attribute_names():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValue=["1"],
        midPointCategoryValue=MP_ENUM,
    )
    data = build_prompt_data(req)
    assert data["app_attr_name"] == "ri:status"
    assert data["app_attr_type"] == "xsd:string"
    assert data["mp_attr_name"] == "c:activation/c:administrativeStatus"


def test_build_prompt_data_lockout_status():
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=BaseSchemaAttribute(name="ri:lockout", type="xsd:string", minOccurs=0, maxOccurs=1),
        midPointAttribute=BaseSchemaAttribute(
            name="c:activation/c:lockoutStatus", type="xsd:string", minOccurs=0, maxOccurs=1
        ),
        inbound=True,
        applicationAttributeValue=["0", "1"],
        midPointCategoryValue=["normal", "locked"],
    )
    data = build_prompt_data(req)
    assert data["mp_enum_values"] == '"normal", "locked"'
    lines = data["app_enum_values"].splitlines()
    assert "'0'" in lines[0]
    assert "'1'" in lines[1]


# ---- suggest_categorical_mapping_script tests ----


@pytest.mark.asyncio
@patch(
    "src.modules.categorical_mapping.service.get_default_llm",
    response_mock(
        '{"description":"Map status to administrativeStatus","transformationScript":"// Map status to administrativeStatus\\nif (input == null) return null\\ninput.equalsIgnoreCase(\\"active\\") ? \\"enabled\\" : input.equalsIgnoreCase(\\"inactive\\") ? \\"disabled\\" : null"}'
    ),
)
async def test_suggest_categorical_mapping_script_smoke(monkeypatch):
    """Smoke test to verify the function doesn't crash and returns valid response."""
    req = SuggestCategoricalMappingRequest(
        applicationAttribute=APP_ATTR,
        midPointAttribute=MP_ATTR,
        inbound=True,
        applicationAttributeValue=["active", "inactive"],
        midPointCategoryValue=MP_ENUM,
    )
    resp = await suggest_categorical_mapping_script(req)
    assert isinstance(resp, SuggestCategoricalMappingResponse)
    assert resp.description == "Map status to administrativeStatus"
    assert resp.transformationScript is not None
