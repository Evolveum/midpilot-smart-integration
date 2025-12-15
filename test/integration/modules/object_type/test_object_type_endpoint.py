# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app import api
from src.config import config
from test.unit.modules.utils import response_mock

_SIMPLE_RULE_JSON = """
{
  "object_class": {
    "name": "ri:group",
    "rules": [
      {
        "kind": "entitlement",
        "intent": "default",
        "displayName": "Default Group",
        "description": "All groups without specific partition.",
        "filter": null,
        "baseContextFilter": null
      }
    ]
  }
}
"""

client = TestClient(api)
base_url = config.app.api_base_url


def test_suggest_object_type_success():
    payload = {
        "schema": {
            "name": "ri:group",
            "description": "Contains group entries",
            "attribute": [
                {"name": "c:attributes/ri:objectClass", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:groupType", "type": "xsd:double", "minOccurs": 0, "maxOccurs": 1},
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
            "coverage": 0.3,
        },
    }

    # Patch LLM to avoid external calls
    with patch("src.modules.object_type.service.get_default_llm", response_mock(_SIMPLE_RULE_JSON)):
        resp = client.post(f"{base_url}/objectType/suggestObjectType", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "objectType" in data and isinstance(data["objectType"], list)

    for suggestion in data["objectType"]:
        assert "kind" in suggestion
        assert "intent" in suggestion
        assert "displayName" in suggestion
        assert "description" in suggestion
        f = suggestion.get("filter")
        assert (f is None) or isinstance(f, list)


def test_suggest_object_type_with_dn_attribute():
    payload = {
        "schema": {
            "name": "ri:user",
            "description": "Contains user entries",
            "attribute": [
                {"name": "c:attributes/ri:objectClass", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:username", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                {"name": "c:attributes/ri:email", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:isActive", "type": "xsd:boolean", "minOccurs": 0, "maxOccurs": 1},
                {
                    "name": "c:attributes/ri:dn",
                    "type": "xsd:string",
                    "minOccurs": 1,
                    "maxOccurs": 1,
                    "description": "Distinguished Name (DN)",
                },
            ],
        },
        "statistics": {
            "attribute": [
                {
                    "ref": "c:attributes/ri:objectClass",
                    "uniqueValueCount": 1,
                    "missingValueCount": 0,
                    "valueCount": [{"value": "user", "count": 1620}],
                },
                {
                    "ref": "c:attributes/ri:isActive",
                    "uniqueValueCount": 2,
                    "missingValueCount": 50,
                    "valueCount": [
                        {"value": "true", "count": 1200},
                        {"value": "false", "count": 370},
                    ],
                },
                {
                    "ref": "c:attributes/ri:email",
                    "uniqueValueCount": 1610,
                    "missingValueCount": 10,
                },
                {
                    "ref": "c:attributes/ri:dn",
                    "uniqueValueCount": 1620,
                    "missingValueCount": 0,
                    "valuePatternCount": [
                        {"value": "ou=People,dc=example,dc=com", "type": "DNsuffix", "count": 1600},
                        {"value": "ou=Admin,dc=example,dc=com", "type": "DNsuffix", "count": 20},
                    ],
                },
            ],
            "attributeTuple": [
                {
                    "ref": ["c:attributes/ri:isActive", "c:attributes/ri:objectClass"],
                    "tupleCount": [
                        {"value": ["true", "user"], "count": 1150},
                        {"value": ["false", "user"], "count": 420},
                    ],
                },
            ],
            "size": 1620,
            "coverage": 1.0,
        },
    }

    # Patch LLM to avoid external calls
    with patch("src.modules.object_type.service.get_default_llm", response_mock(_SIMPLE_RULE_JSON)):
        resp = client.post(f"{base_url}/objectType/suggestObjectType", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "objectType" in data and isinstance(data["objectType"], list)

    for suggestion in data["objectType"]:
        assert "kind" in suggestion
        assert "intent" in suggestion
        assert "displayName" in suggestion
        assert "description" in suggestion
