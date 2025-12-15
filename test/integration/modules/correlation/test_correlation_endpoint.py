# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api

_EXT_ATTRIBUTES = [
    {
        "name": "c:extension/ext:personalNumber",
        "type": "xsd:string",
        "description": "Unique personal number assigned by HR.",
        "minOccurs": 0,
        "maxOccurs": 1,
    },
    {
        "name": "c:extension/ext:email",
        "type": "xsd:string",
        "description": "Corporate email address.",
        "minOccurs": 0,
        "maxOccurs": 1,
    },
]

_STATS = {
    "c:extension/ext:personalNumber": {"totalCount": 1000, "nuniq": 995, "nmissing": 5},
    "c:extension/ext:email": {"totalCount": 1000, "nuniq": 980, "nmissing": 20},
}


def test_suggest_extension_correlators_endpoint_integration() -> None:
    client = TestClient(api)

    payload = {
        "schemaName": "c:UserType",
        "schemaDescription": "User type with typical HR-driven extensions",
        "extensionAttributes": _EXT_ATTRIBUTES,
        "attributeStats": _STATS,
    }

    resp = client.post("/api/v1/correlation/suggestExtensionCorrelators", json=payload)
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert isinstance(data, dict), data
    assert "correlators" in data, data

    correlators = data["correlators"]
    assert isinstance(correlators, list), correlators
    assert all(isinstance(c, str) for c in correlators), correlators

    # Correlators should reference provided extension attribute names
    ext_names = {a["name"] for a in _EXT_ATTRIBUTES}
    assert all(c in ext_names for c in correlators), (correlators, ext_names)

    # No duplicates and at least one result is returned
    assert len(set(correlators)) == len(correlators), correlators
    assert len(correlators) >= 1
