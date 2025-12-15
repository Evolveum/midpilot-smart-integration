# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api
from src.config import config
from src.modules.focus_type.schema import FocusType

client = TestClient(api)
base_url = config.app.api_base_url


def test_suggest_focus_type_success():
    payload = {
        "kind": "account",
        "intent": "default",
        "baseContextFilter": "attributes/name = 'main'",
        "schema": {
            "name": "ri:account",
            "description": "Contains user accounts",
            "attribute": [
                {"name": "c:attributes/ri:phone", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:department", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:personalNumber", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:email", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                {"name": "c:attributes/ri:created", "type": "xsd:dateTime", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:status", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/ri:description", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/icfs:name", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                {"name": "c:attributes/ri:type", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {
                    "name": "c:attributes/ri:fullname",
                    "type": "xsd:string",
                    "description": "User's full name",
                    "minOccurs": 1,
                    "maxOccurs": 1,
                },
                {"name": "c:attributes/ri:lastLogin", "type": "xsd:dateTime", "minOccurs": 0, "maxOccurs": 1},
                {"name": "c:attributes/icfs:uid", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                {
                    "name": "c:credentials/c:password/c:value",
                    "type": "xsd:string",
                    "minOccurs": 0,
                    "maxOccurs": 1,
                },
                {
                    "name": "c:activation/c:administrativeStatus",
                    "type": "xsd:string",
                    "minOccurs": 0,
                    "maxOccurs": 1,
                },
            ],
        },
    }
    resp = client.post(f"{base_url}/focusType/suggestFocusType", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "focusTypeName" in data
    assert data["focusTypeName"] in [ft.value for ft in FocusType]
