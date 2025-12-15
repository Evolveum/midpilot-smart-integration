# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from unittest.mock import patch

import pytest

from src.common.errors import LLMResponseValidationException
from src.modules.matching.schema import MatchSchemaRequest, SchemaAttributeMatch
from src.modules.matching.service import build_match_schema_prompt_data, match_midpoint_schema
from test.unit.modules.utils import response_mock

# IGA (Active Directory ↔ MidPoint) base schemas
_AD_JSON_SCHEMA = {
    "sAMAccountName": {"type": "xsd:string", "description": "Logon name for backward compatibility."},
    "cn": {"type": "xsd:string", "description": "User's common name (full name)."},
    "mail": {"type": "xsd:string", "description": "Primary email address."},
    "telephoneNumber": {"type": "xsd:string", "description": "Office phone number."},
    "mobile": {"type": "xsd:string", "description": "Mobile phone number."},
    "department": {"type": "xsd:string", "description": "Department name."},
    "distinguishedName": {"type": "xsd:string", "description": "LDAP DN (e.g., OU=Sales,DC=example,DC=com)."},
}
_MIDPOINT_JSON_SCHEMA = {
    "c:uid": {"type": "xsd:string", "description": "Unique user identifier in MidPoint."},
    "c:name": {"type": "xsd:string", "description": "User's full name."},
    "c:emailAddress": {"type": "xsd:string", "description": "Email address."},
    "c:telephoneNumber": {"type": "xsd:string", "description": "Phone number."},
    "c:organizationalUnit": {"type": "xsd:string", "description": "Organizational unit within MidPoint."},
    "c:employeeNumber": {"type": "xsd:string", "description": "Employee number for payroll systems."},
}


basic_req = MatchSchemaRequest(
    applicationSchema={
        "name": "ad_account",
        "description": "Active Directory user schema",
        "attribute": [
            {"name": k, "type": v["type"], "description": v["description"], "minOccurs": 0, "maxOccurs": 1}
            for k, v in _AD_JSON_SCHEMA.items()
        ],
    },
    midPointSchema={
        "name": "c:UserType",
        "description": "MidPoint user type schema",
        "attribute": [
            {"name": k, "type": v["type"], "description": v["description"], "minOccurs": 0, "maxOccurs": 1}
            for k, v in _MIDPOINT_JSON_SCHEMA.items()
        ],
    },
)


# Empty schema build
_empty_req = MatchSchemaRequest(
    applicationSchema={"name": "ad_account", "description": "Active Directory user schema", "attribute": []},
    midPointSchema={"name": "c:UserType", "description": "MidPoint user type schema", "attribute": []},
)


def test_build_match_schema_prompt_data_empty():
    data = build_match_schema_prompt_data(_empty_req)
    assert data["Resource_schema"] == {}
    assert data["MidPoint_schema"] == {}


# Test: LLM hallucinations ignored
_HALLU_JSON = json.dumps(
    {
        "pairs": [
            {"MidPoint": "c:unknownAttr", "Resource": ["bogusAttr"]},
            {"MidPoint": "c:uid", "Resource": ["sAMAccountName", "bogusAttr"]},
        ]
    },
    indent=2,
)


@pytest.mark.asyncio
@patch("src.modules.matching.service.get_default_llm", response_mock(_HALLU_JSON))
async def test_ignore_hallucinated_attributes():
    resp = await match_midpoint_schema(basic_req)
    expected = [SchemaAttributeMatch(midPointAttribute="c:uid", applicationAttribute="sAMAccountName")]
    assert resp.attributeMatch == expected


# Test: Multiple pairs for the same MidPoint
_MULTI_PAIR_JSON = json.dumps(
    {
        "pairs": [
            {"MidPoint": "c:telephoneNumber", "Resource": ["telephoneNumber"]},
            {"MidPoint": "c:telephoneNumber", "Resource": ["mobile"]},
        ]
    },
    indent=2,
)


@pytest.mark.asyncio
@patch("src.modules.matching.service.get_default_llm", response_mock(_MULTI_PAIR_JSON))
async def test_multiple_pairs_same_midpoint():
    resp = await match_midpoint_schema(basic_req)
    expected = [
        SchemaAttributeMatch(midPointAttribute="c:telephoneNumber", applicationAttribute="mobile"),
        SchemaAttributeMatch(midPointAttribute="c:telephoneNumber", applicationAttribute="telephoneNumber"),
    ]
    resp.attributeMatch.sort(key=lambda m: m.applicationAttribute)
    assert resp.attributeMatch == expected


# Test: Duplicate resources within one pair deduplicated
_DUPLICATE_JSON = json.dumps({"pairs": [{"MidPoint": "c:name", "Resource": ["cn", "cn"]}]}, indent=2)


@pytest.mark.asyncio
@patch("src.modules.matching.service.get_default_llm", response_mock(_DUPLICATE_JSON))
async def test_grouped_duplicates_removed():
    resp = await match_midpoint_schema(basic_req)
    expected = [SchemaAttributeMatch(midPointAttribute="c:name", applicationAttribute="cn")]
    assert resp.attributeMatch == expected


# Test: Full example grouping
_FULL_JSON = json.dumps(
    {
        "pairs": [
            {"MidPoint": "c:uid", "Resource": ["sAMAccountName"]},
            {"MidPoint": "c:name", "Resource": ["cn"]},
            {"MidPoint": "c:emailAddress", "Resource": ["mail"]},
            {"MidPoint": "c:telephoneNumber", "Resource": ["telephoneNumber", "mobile"]},
            {"MidPoint": "c:organizationalUnit", "Resource": ["department", "distinguishedName"]},
            {"MidPoint": "c:employeeNumber", "Resource": []},
        ]
    },
    indent=2,
)


@pytest.mark.asyncio
@patch("src.modules.matching.service.get_default_llm", response_mock(_FULL_JSON))
async def test_full_grouped_example():
    resp = await match_midpoint_schema(basic_req)

    # Flattened matches count:
    # 1 + 1 + 1 + 2 + 2 = 7
    assert len(resp.attributeMatch) == 7

    mapping = {(m.midPointAttribute, m.applicationAttribute) for m in resp.attributeMatch}
    expected = {
        ("c:uid", "sAMAccountName"),
        ("c:name", "cn"),
        ("c:emailAddress", "mail"),
        ("c:telephoneNumber", "telephoneNumber"),
        ("c:telephoneNumber", "mobile"),
        ("c:organizationalUnit", "department"),
        ("c:organizationalUnit", "distinguishedName"),
    }
    assert mapping == expected


@pytest.mark.asyncio
@patch("src.modules.matching.service.get_default_llm", response_mock('{ invalid: "json" }'))
async def test_invalid_json_response():
    with pytest.raises(LLMResponseValidationException):
        await match_midpoint_schema(basic_req)
