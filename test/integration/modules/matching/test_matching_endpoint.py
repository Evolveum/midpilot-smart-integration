# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api
from src.config import config

client = TestClient(api)
base_url = config.app.api_base_url


def test_match_schemas_endpoint_shape():
    payload = {
        "applicationSchema": {
            "name": "account",
            "description": "Test resource schema",
            "attribute": [
                {"name": "username", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "email", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "phone", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
            ],
        },
        "midPointSchema": {
            "name": "c:UserType",
            "description": "Test MidPoint schema",
            "attribute": [
                {"name": "c:uid", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:emailAddress", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:telephoneNumber", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
            ],
        },
    }

    resp = client.post(f"{base_url}/matching/matchSchema", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    # The endpoint returns a MatchSchemaResponse, so top‐level key is attributeMatch
    assert "attributeMatch" in data
    assert isinstance(data["attributeMatch"], list)

    # Each entry should have midPointAttribute and applicationAttribute strings
    for match in data["attributeMatch"]:
        assert "midPointAttribute" in match and isinstance(match["midPointAttribute"], str)
        assert "applicationAttribute" in match and isinstance(match["applicationAttribute"], str)
