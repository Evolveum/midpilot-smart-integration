# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from unittest.mock import patch

import pytest

from src.common.errors import LLMResponseValidationException
from src.modules.object_type.schema import (
    ObjectTypeSuggestion,
    SuggestObjectTypeRequest,
    SuggestObjectTypeResponse,
)
from src.modules.object_type.service import (
    build_object_type_prompt_data,
    suggest_delineation,
)
from test.unit.modules.utils import response_mock

_BASIC_REQ = {
    "schema": {"name": "ri:group", "description": "Test groups", "attribute": []},
    "statistics": {"attribute": [], "attributeTuple": [], "size": 2, "coverage": 1.0},
}
request = SuggestObjectTypeRequest(**_BASIC_REQ)


def test_build_object_type_prompt_data_empty():
    expected = {
        "objectClass": "ri:group",
        "schema": {
            "attributes": [],
        },
        "count": 2,
        "statistics": [],
        "crosstabs": [],
    }
    assert build_object_type_prompt_data(request) == expected


_FULL_REQ = {
    "schema": {
        "name": "ri:group",
        "description": "Contains group entries",
        "attribute": [
            {"name": "c:attributes/ri:objectClass", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
            {"name": "c:attributes/ri:groupType", "type": "xsd:double", "minOccurs": 1, "maxOccurs": 1},
            {"name": "c:attributes/ri:adminDescription", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
        ],
    },
    "statistics": {
        "attribute": [
            {
                "ref": "c:attributes/ri:groupType",
                "uniqueValueCount": 4,
                "missingValueCount": 0,
                "valueCount": [
                    {"value": "-2147483646.0", "count": 1395},
                    {"value": "8.0", "count": 238},
                ],
                "valuePatternCount": [
                    {"value": "int", "type": "prefix", "count": 100},
                    {"value": "admin", "type": "suffix", "count": 20},
                ],
            },
        ],
        "attributeTuple": [
            {
                "ref": ["c:attributes/ri:loginShell", "c:attributes/ri:objectClass"],
                "tupleCount": [
                    {"value": ["false", "user"], "count": 872},
                    {"value": ["true", "user"], "count": 828},
                ],
            },
        ],
        "size": 1670,
        "coverage": 1,
    },
}


def test_build_full_object_type_prompt_data_empty():
    full_request = SuggestObjectTypeRequest(**_FULL_REQ)
    expected = {
        "objectClass": "ri:group",
        "schema": {
            "attributes": [
                {"name": "c:attributes/ri:objectClass", "type": "xsd:string"},
                {"name": "c:attributes/ri:groupType", "type": "xsd:double"},
                {"name": "c:attributes/ri:adminDescription", "type": "xsd:string"},
            ],
        },
        "count": 1670,
        "statistics": [
            {
                "column": "c:attributes/ri:groupType",
                "uniqueCount": 4,
                "uniqueRatio": 0.0023952095808383233,
                "missingCount": 0,
                "missingRatio": 0.0,
                "topN": 2,
                "values": [
                    {"count": 1395, "value": "-2147483646.0"},
                    {"count": 238, "value": "8.0"},
                ],
                "patterns": [
                    {"value": "int", "type": "prefix", "count": 100},
                    {"value": "admin", "type": "suffix", "count": 20},
                ],
            }
        ],
        "crosstabs": [
            {
                "ref": ("c:attributes/ri:loginShell", "c:attributes/ri:objectClass"),
                "counts": [
                    {"count": 872, "value": ("false", "user")},
                    {"count": 828, "value": ("true", "user")},
                ],
            }
        ],
    }
    assert build_object_type_prompt_data(full_request) == expected


_SINGLE_RULE_JSON = json.dumps(
    {
        "object_class": {
            "name": "ri:group",
            "rules": [
                {
                    "kind": "entitlement",
                    "intent": "security",
                    "displayName": "Security Entitlement",
                    "description": "Grants or restricts access to security-related features, permissions, or resources within the system. This entitlement determines a user's or application's authorization to perform specific security-sensitive actions.",
                    "filter": ["ruleA"],
                    "baseContextFilter": None,
                }
            ],
        }
    },
    indent=2,
)


_NO_RULES_JSON = json.dumps({"object_class": {"name": "ri:group", "rules": []}}, indent=2)
_INVALID_JSON = "not valid json"


@pytest.mark.asyncio
@patch("src.modules.object_type.service.get_default_llm", response_mock(_SINGLE_RULE_JSON))
async def test_suggest_delineation_single_rule():
    resp = await suggest_delineation(request)
    assert resp == SuggestObjectTypeResponse(
        objectType=[
            ObjectTypeSuggestion(
                kind="entitlement",
                intent="security",
                displayName="Security Entitlement",
                description="Grants or restricts access to security-related features, permissions, or resources within the system. This entitlement determines a user's or application's authorization to perform specific security-sensitive actions.",
                filter=["ruleA"],
                baseContextFilter=None,
                baseContextObjectClassName=None,
            )
        ]
    )


@pytest.mark.asyncio
@patch("src.modules.object_type.service.get_default_llm", response_mock(_NO_RULES_JSON))
async def test_suggest_delineation_no_rules_returns_empty():
    resp = await suggest_delineation(request)
    assert resp.objectType == []


@pytest.mark.asyncio
@patch("src.modules.object_type.service.get_default_llm", response_mock(_INVALID_JSON))
async def test_suggest_delineation_bad_json_raises():
    with pytest.raises(LLMResponseValidationException):
        await suggest_delineation(request)


@pytest.mark.asyncio
@patch("src.modules.object_type.service.get_default_llm", response_mock(_SINGLE_RULE_JSON))
async def test_suggest_delineation_with_feedback():
    # Construct a request identical to the basic one and include empty validationErrorFeedback to exercise feedback handling
    req = SuggestObjectTypeRequest(
        **{
            **_BASIC_REQ,
            "validationErrorFeedback": [],
        }
    )
    resp = await suggest_delineation(req)
    assert resp == SuggestObjectTypeResponse(
        objectType=[
            ObjectTypeSuggestion(
                kind="entitlement",
                intent="security",
                displayName="Security Entitlement",
                description="Grants or restricts access to security-related features, permissions, or resources within the system. This entitlement determines a user's or application's authorization to perform specific security-sensitive actions.",
                filter=["ruleA"],
                baseContextFilter=None,
                baseContextObjectClassName=None,
            )
        ]
    )
