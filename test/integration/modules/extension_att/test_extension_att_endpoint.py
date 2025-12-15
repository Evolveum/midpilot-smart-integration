# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api
from src.config import config

client = TestClient(api)
base_url = config.app.api_base_url


def test_suggest_extension_endpoint_shape():
    payload = {
        "applicationSchema": {
            "name": "google",
            "description": "Test resource schema with UNMAPPED attributes",
            "attribute": [
                {
                    "name": "c:attributes/ri:personalNumber",
                    "type": "xsd:string",
                    "minOccurs": 0,
                    "maxOccurs": 1,
                    "description": "Employee personal number.",
                },
                {
                    "name": "c:attributes/ri:department",
                    "type": "xsd:string",
                    "minOccurs": 0,
                    "maxOccurs": 1,
                },
                {
                    "name": "c:attributes/ri:lastLogin",
                    "type": "xsd:dateTime",
                    "minOccurs": 0,
                    "maxOccurs": 1,
                },
            ],
        },
        "attributeStats": {
            "c:attributes/ri:personalNumber": {"totalCount": 1000, "nuniq": 1000, "nmissing": 0},
            "c:attributes/ri:department": {"totalCount": 1000, "nuniq": 12, "nmissing": 5},
            "c:attributes/ri:lastLogin": {"totalCount": 1000, "nuniq": 980, "nmissing": 20},
        },
    }

    resp = client.post(f"{base_url}/extensionAttributes/suggestExtensionAttributes", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "extensionAttributes" in data
    assert isinstance(data["extensionAttributes"], list)

    for name in data["extensionAttributes"]:
        assert isinstance(name, str)
        assert name.strip()
