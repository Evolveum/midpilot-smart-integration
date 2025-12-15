# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from unittest.mock import patch

import pytest

from src.modules.mapping.schema import (
    IOExample,
    MappingSchemaAttribute,
    SuggestMappingRequest,
    SuggestMappingResponse,
    ValueExample,
)
from src.modules.mapping.service import build_prompt_data, suggest_mapping_script
from test.unit.modules.utils import response_mock

# ---- build_prompt_data tests (deterministické) ----


def test_build_prompt_data_single_presence_to_bool():
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="manager", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="hasManager", type="xsd:boolean", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[
            IOExample(
                application=[ValueExample(name="manager", value=["Alice"])],
                midPoint=[ValueExample(name="hasManager", value=["true"])],
            ),
            IOExample(
                # missing application → application=None
                midPoint=[ValueExample(name="hasManager", value=["false"])]
            ),
        ],
    )
    expected = '[input: "Alice"] -> true\n[input: null] -> false'
    assert build_prompt_data(req).strip() == expected


def test_build_prompt_data_missing_midpoint_or_application():
    # missing midPoint entirely → target null
    req1 = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="attr", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="out", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[
            IOExample(
                application=[ValueExample(name="attr", value=["ValueOnly"])],
            )
        ],
    )
    assert build_prompt_data(req1).strip() == '[input: "ValueOnly"] -> null'

    # missing application entirely → source null
    req2 = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="attr", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="out", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[IOExample(midPoint=[ValueExample(name="out", value=["TARGET"])])],
    )
    assert build_prompt_data(req2).strip() == '[input: null] -> "TARGET"'


def test_build_prompt_data_all_empty_examples():
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="firstName", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="givenName", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[IOExample(), IOExample(), IOExample()],
    )
    expected = "[input: null] -> null\n[input: null] -> null\n[input: null] -> null"
    assert build_prompt_data(req).strip() == expected


def test_build_prompt_data_inbound_simple():
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="firstName", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="givenName", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[
            IOExample(
                application=[ValueExample(name="firstName", value=["John"])],
                midPoint=[ValueExample(name="givenName", value=["JOHN"])],
            ),
            IOExample(
                application=[ValueExample(name="firstName", value=["Jane"])],
                midPoint=[ValueExample(name="givenName", value=["JANE"])],
            ),
        ],
    )
    expected = '[input: "John"] -> "JOHN"\n[input: "Jane"] -> "JANE"'
    assert build_prompt_data(req).strip() == expected


def test_build_prompt_data_outbound_simple():
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="firstName", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="givenName", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=False,
        example=[
            IOExample(
                application=[ValueExample(name="firstName", value=["John"])],
                midPoint=[ValueExample(name="givenName", value=["JOHN"])],
            )
        ],
    )
    # outbound = midPoint → application
    assert build_prompt_data(req).strip() == '[givenName: "JOHN"] -> "John"'


def test_build_prompt_data_boolean_mapping():
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="flag", type="xsd:boolean", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="otherFlag", type="xsd:boolean", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[
            IOExample(
                application=[ValueExample(name="flag", value=["true"])],
                midPoint=[ValueExample(name="otherFlag", value=["false"])],
            )
        ],
    )
    assert build_prompt_data(req).strip() == "[input: true] -> false"


def test_build_prompt_data_multivalued_to_single_valued():
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="nums", type="xsd:int", minOccurs=1, maxOccurs=-1)],
        midPointAttribute=[MappingSchemaAttribute(name="out", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=False,
        example=[
            IOExample(
                application=[ValueExample(name="nums", value=["1", "2", "3"])],
                midPoint=[ValueExample(name="out", value=["ONE_TWO_THREE"])],
            )
        ],
    )
    # left = midPoint hodnota, right = application hodnota
    assert build_prompt_data(req).strip() == '[out: "ONE_TWO_THREE"] -> [1, 2, 3]'


def test_build_prompt_data_single_to_multivalued():
    # application single, midpoint multivalued (outbound)
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="tag", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="labels", type="xsd:string", minOccurs=0, maxOccurs=-1)],
        inbound=False,
        example=[
            IOExample(
                application=[ValueExample(name="tag", value=["urgent"])],
                midPoint=[ValueExample(name="labels", value=["URGENT", "IMPORTANT"])],
            )
        ],
    )
    assert build_prompt_data(req).strip() == '[labels: ["URGENT", "IMPORTANT"]] -> "urgent"'


def test_build_prompt_data_multivalued_to_multivalued():
    # both sides multivalued (outbound)
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="nums", type="xsd:int", minOccurs=1, maxOccurs=-1)],
        midPointAttribute=[MappingSchemaAttribute(name="outs", type="xsd:int", minOccurs=0, maxOccurs=-1)],
        inbound=False,
        example=[
            IOExample(
                application=[ValueExample(name="nums", value=["1", "2"])],
                midPoint=[ValueExample(name="outs", value=["10", "20"])],
            )
        ],
    )
    assert build_prompt_data(req).strip() == "[outs: [10, 20]] -> [1, 2]"


# ---- full script suggestion tests ----
@pytest.mark.asyncio
@patch(
    "src.modules.mapping.service.get_default_llm",
    response_mock(
        '{"description":"Uppercase input","transformationScript":"// Uppercase input\\ninput.toUpperCase()"}'
    ),
)
async def test_suggest_mapping_script_inbound(monkeypatch):
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="firstName", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="givenName", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[
            IOExample(
                application=[ValueExample(name="firstName", value=["John"])],
                midPoint=[ValueExample(name="givenName", value=["JOHN"])],
            )
        ],
        errorLog="Simulated backend validation error for inbound test",
        previousScript="// Uppercase input\ninput.firstName?.toUpperCase()",
    )
    resp = await suggest_mapping_script(req)
    assert resp == SuggestMappingResponse(
        description="Uppercase input", transformationScript="// Uppercase input\ninput.toUpperCase()"
    )


@pytest.mark.asyncio
@patch(
    "src.modules.mapping.service.get_default_llm",
    response_mock(
        '{"description":"Uppercase firstName","transformationScript":"// Uppercase firstName\\nfirstName.toUpperCase()"}'
    ),
)
async def test_suggest_mapping_script_outbound(monkeypatch):
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="firstName", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="givenName", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=False,
        example=[
            IOExample(
                application=[ValueExample(name="firstName", value=["John"])],
                midPoint=[ValueExample(name="givenName", value=["JOHN"])],
            )
        ],
        errorLog="Simulated backend validation error for outbound test",
        previousScript="// Uppercase firstName\ninput?.toUpperCase()",
    )
    resp = await suggest_mapping_script(req)
    assert resp == SuggestMappingResponse(
        description="Uppercase firstName", transformationScript="// Uppercase firstName\nfirstName.toUpperCase()"
    )


@pytest.mark.asyncio
@patch(
    "src.modules.mapping.service.get_default_llm",
    response_mock(
        """{"description":"Check input presence","transformationScript":"// Check input presence\\ninput != null && input != ''"}"""
    ),
)
async def test_suggest_mapping_script_has_manager_single(monkeypatch):
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="manager", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="hasManager", type="xsd:boolean", minOccurs=0, maxOccurs=1)],
        inbound=True,
        example=[
            IOExample(
                application=[ValueExample(name="manager", value=["Alice"])],
                midPoint=[ValueExample(name="hasManager", value=["true"])],
            ),
            IOExample(midPoint=[ValueExample(name="hasManager", value=["false"])]),
        ],
        errorLog="Simulated backend validation error for manager test",
        previousScript="// Check input presence\nreturn input ? true : false",
    )
    resp = await suggest_mapping_script(req)
    assert resp == SuggestMappingResponse(
        description="Check input presence",
        transformationScript="// Check input presence\ninput != null && input != ''",
    )


@pytest.mark.asyncio
@patch(
    "src.modules.mapping.service.get_default_llm",
    response_mock(
        '{"description":"Normalize email","transformationScript":"// Normalize email\\n(email instanceof String ? email.trim().toLowerCase() : null)"}'
    ),
)
async def test_suggest_mapping_script_previous_without_errorlog(monkeypatch):
    req = SuggestMappingRequest(
        applicationAttribute=[MappingSchemaAttribute(name="email", type="xsd:string", minOccurs=1, maxOccurs=1)],
        midPointAttribute=[MappingSchemaAttribute(name="normalizedEmail", type="xsd:string", minOccurs=0, maxOccurs=1)],
        inbound=False,
        example=[
            IOExample(
                application=[ValueExample(name="email", value=[" User@ExAmPle.com "])],
                midPoint=[ValueExample(name="normalizedEmail", value=["user@example.com"])],
            )
        ],
        previousScript="// Normalize email\ncontext['email']?.trim()?.toLowerCase()",
    )
    resp = await suggest_mapping_script(req)
    assert resp == SuggestMappingResponse(
        description="Normalize email",
        transformationScript="// Normalize email\n(email instanceof String ? email.trim().toLowerCase() : null)",
    )
