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
        "applicationAttributeValue": ["active", "inactive", "deleted"],
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
        "applicationAttributeValue": ["0", "1"],
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
        "applicationAttributeValue": [],
        "midPointCategoryValue": ["enabled", "disabled", "archived"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "description" in data
    assert "transformationScript" in data


def test_suggest_categorical_mapping_endpoint_no_meaningful_mapping():
    payload = {
        "applicationAttribute": {"name": "ri:departmentCode", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
        "midPointAttribute": {
            "name": "c:activation/c:administrativeStatus",
            "type": "xsd:string",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        "inbound": True,
        "applicationAttributeValue": ["DEPT-001", "DEPT-002", "DEPT-003"],
        "midPointCategoryValue": ["enabled", "disabled", "archived"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "description" in data
    assert "transformationScript" in data
    assert data["transformationScript"] is None


def test_suggest_categorical_mapping_endpoint_missing_required_fields():
    payload = {
        "inbound": True,
        "midPointCategoryValue": ["enabled", "disabled"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 422


def test_suggest_categorical_mapping_endpoint_outbound_not_supported():
    payload = {
        "applicationAttribute": {"name": "ri:status", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
        "midPointAttribute": {
            "name": "c:activation/c:administrativeStatus",
            "type": "xsd:string",
            "minOccurs": 0,
            "maxOccurs": 1,
        },
        "inbound": False,
        "applicationAttributeValue": ["active", "inactive"],
        "midPointCategoryValue": ["enabled", "disabled", "archived"],
    }

    resp = client.post(f"{base_url}/mapping/suggestCategoricalMapping", json=payload)
    assert resp.status_code == 422

    data = resp.json()
    assert "detail" in data
    assert any("inbound" in str(error.get("loc", [])) for error in data["detail"])
    assert any("not yet supported" in error.get("msg", "").lower() for error in data["detail"])
