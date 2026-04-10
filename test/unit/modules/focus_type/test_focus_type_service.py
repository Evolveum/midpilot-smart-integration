# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from unittest.mock import patch

import pytest

from src.common.errors import LLMResponseValidationException
from src.common.schema import ModelOptions
from src.modules.focus_type.schema import (
    FocusType,
    SuggestFocusTypeRequest,
    SuggestFocusTypeResponse,
)
from src.modules.focus_type.service import (
    build_focus_type_prompt_data,
    suggest_focus_type,
)
from test.unit.modules.utils import response_mock

request = SuggestFocusTypeRequest(
    **{
        "kind": "account",
        "intent": "default",
        "baseContextFilter": "attributes/name = 'main'",
        "schema": {
            "name": "ri:account",
            "description": "Contains user accounts",
            "attribute": [
                {"name": "c:attributes/ri:phone", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:name", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:email", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {
                    "name": "c:attributes/ri:fullname",
                    "type": "xsd:string",
                    "description": "User's full name",
                    "minOccurs": 1,
                    "maxOccurs": 1,
                },
                {"name": "c:attributes/ri:uid", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
            ],
        },
    }
)


@pytest.mark.asyncio
@patch("src.modules.focus_type.service.get_default_llm", response_mock('{"focusTypeName": "UserType"}'))
async def test_suggest_single_focus_type():
    response = await suggest_focus_type(request)
    assert response == SuggestFocusTypeResponse(focusTypeName=FocusType.UserType)


@pytest.mark.asyncio
@patch("src.modules.focus_type.service.get_default_llm", response_mock('{"focusTypeName": "OrgType"}'))
async def test_suggest_org_focus_type():
    response = await suggest_focus_type(request)
    assert response == SuggestFocusTypeResponse(focusTypeName=FocusType.OrgType)


@pytest.mark.asyncio
@patch("src.modules.focus_type.service.get_default_llm", response_mock('["Invalid"]'))
async def test_invalid_focus_type_error():
    with pytest.raises(LLMResponseValidationException):
        await suggest_focus_type(request)


@pytest.mark.asyncio
@patch("src.modules.focus_type.service.get_default_llm", response_mock('{"focusType": ["UserType"]}'))
async def test_focus_type_format_error():
    with pytest.raises(LLMResponseValidationException):
        await suggest_focus_type(request)


@pytest.mark.asyncio
@patch("src.modules.focus_type.service.get_default_llm", response_mock('["OrgType", "UserType"'))
async def test_focus_type_parsing_error():
    with pytest.raises(LLMResponseValidationException):
        await suggest_focus_type(request)


expected_prompt_data = {
    "objectClass": "ri:account",
    "kind": "account",
    "intent": "default",
    "attributes": [
        "c:attributes/ri:phone",
        "c:attributes/ri:name",
        "c:attributes/ri:email",
        "c:attributes/ri:fullname",
        "c:attributes/ri:uid",
    ],
    "delineation": "attributes/name = 'main'",
}


def test_build_full_prompt_data():
    actual_data = build_focus_type_prompt_data(request)
    assert actual_data == expected_prompt_data


@pytest.mark.asyncio
@patch("src.modules.focus_type.service.get_default_llm")
async def test_model_options_forwarded_to_llm(mock_get_default_llm):
    mock_get_default_llm.return_value = response_mock('{"focusTypeName": "UserType"}').return_value
    model_options = ModelOptions(modelName="custom-model", reasoningEffort="low")
    req = request.model_copy(update={"modelOptions": model_options})
    await suggest_focus_type(req)
    mock_get_default_llm.assert_called_once_with(model_options=model_options)
