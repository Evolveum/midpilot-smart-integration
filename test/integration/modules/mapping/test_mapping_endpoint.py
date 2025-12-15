# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api
from src.config import config

client = TestClient(api)
base_url = config.app.api_base_url


def test_suggest_mapping_endpoint_shape():
    payload = {
        "applicationAttribute": [{"name": "firstName", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1}],
        "midPointAttribute": [{"name": "given_name", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1}],
        "inbound": True,
        "example": [
            {
                "application": [{"name": "firstName", "value": ["John"]}],
                "midPoint": [{"name": "given_name", "value": ["JOHN"]}],
            },
            {
                "application": [{"name": "firstName", "value": ["Jane"]}],
                "midPoint": [{"name": "given_name", "value": ["JANE"]}],
            },
        ],
        "errorLog": "Simulated backend validation error for mapping endpoint test",
        "previousScript": "// Uppercase given name\ninput.firstName?.toUpperCase()",
    }

    resp = client.post(f"{base_url}/mapping/suggestMapping", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "description" in data
    assert isinstance(data["description"], str)
    assert data["description"].strip() != ""

    assert "transformationScript" in data
    assert isinstance(data["transformationScript"], str)
    script = data["transformationScript"]
    assert script.strip() != ""

    first_line = script.splitlines()[0]
    assert first_line == f"// {data['description']}"
