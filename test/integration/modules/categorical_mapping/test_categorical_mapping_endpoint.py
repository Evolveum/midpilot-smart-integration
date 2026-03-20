# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api
from src.config import config

client = TestClient(api)
base_url = config.app.api_base_url


def test_suggest_categorical_mapping_endpoint_shape():
    payload = {
        "applicationAttribute": {"name": "ri:status", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
        "midPointAttribute": {
            "name": "c:activation/c:administrativeStatus",
            "type": "xsd:string",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        "inbound": True,
        "applicationAttributeValueCount": [
            {"value": "active", "count": 100},
            {"value": "inactive", "count": 45},
            {"value": "deleted", "count": 5},
        ],
        "midPointCategoryValue": ["enabled", "disabled", "archived"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "description" in data
    assert isinstance(data["description"], str)
    assert data["description"].strip() != ""

    assert "transformationScript" in data
    script = data["transformationScript"]
    assert script is not None
    assert isinstance(script, str)

    first_line = script.splitlines()[0]
    assert first_line == f"// {data['description']}"


def test_suggest_categorical_mapping_endpoint_lockout():
    payload = {
        "applicationAttribute": {"name": "ri:lockoutStatus", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
        "midPointAttribute": {
            "name": "c:activation/c:lockoutStatus",
            "type": "xsd:string",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        "inbound": True,
        "applicationAttributeValueCount": [
            {"value": "0", "count": 980},
            {"value": "1", "count": 20},
        ],
        "midPointCategoryValue": ["normal", "locked"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "description" in data
    assert "transformationScript" in data


def test_suggest_categorical_mapping_endpoint_empty_counts():
    payload = {
        "applicationAttribute": {"name": "ri:status", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
        "midPointAttribute": {
            "name": "c:activation/c:administrativeStatus",
            "type": "xsd:string",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        "inbound": True,
        "applicationAttributeValueCount": [],
        "midPointCategoryValue": ["enabled", "disabled", "archived"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "description" in data
    assert "transformationScript" in data


def test_suggest_categorical_mapping_endpoint_missing_required_fields():
    payload = {
        "inbound": True,
        "midPointCategoryValue": ["enabled", "disabled"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 422
