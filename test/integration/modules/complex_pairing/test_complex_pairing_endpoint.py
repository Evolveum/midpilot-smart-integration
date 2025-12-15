# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi.testclient import TestClient

from src.app import api
from src.config import config

client = TestClient(api)
base_url = config.app.api_base_url


def test_complex_pairing_endpoint() -> None:
    payload = {
        "pairs": [
            {
                "midPoint": [
                    {
                        "identifier": "1",
                        "content": [
                            {"attribute": "c:email[*]/value", "value": ["anna.novakova@firma.sk"]},
                            {"attribute": "c:email[*]/type", "value": ["work"]},
                        ],
                    }
                ],
                "application": [
                    {
                        "identifier": "A1",
                        "content": [
                            {"attribute": "c:primaryEmail/address", "value": ["ANNA.NOVAKOVA@FIRMA.SK"]},
                            {"attribute": "c:primaryEmail/category", "value": ["work"]},
                        ],
                    }
                ],
            },
            {
                "midPoint": [
                    {
                        "identifier": "2",
                        "content": [
                            {"attribute": "c:email[*]/value", "value": ["adam.kral4@startup.io"]},
                            {"attribute": "c:email[*]/type", "value": ["work"]},
                        ],
                    }
                ],
                "application": [
                    {
                        "identifier": "B1",
                        "content": [
                            {"attribute": "c:primaryEmail/address", "value": ["ADAM.KRAL4@STARTUP.IO"]},
                            {"attribute": "c:primaryEmail/category", "value": ["work"]},
                        ],
                    }
                ],
            },
        ]
    }

    resp = client.post(f"{base_url}/complexPairing/complexPairing", json=payload)
    assert resp.status_code == 200

    data = resp.json()

    assert "similar" in data and "rationale" in data and "mappings" in data
    assert isinstance(data["similar"], bool)
    assert isinstance(data["rationale"], str) and data["rationale"].strip() != ""
    assert isinstance(data["mappings"], list)

    allowed_mid = {"1", "2"}
    allowed_app = {"A1", "B1"}

    assert len(data["mappings"]) >= 1

    for m in data["mappings"]:
        assert "midPointIdentifier" in m and "applicationIdentifier" in m
        assert isinstance(m["midPointIdentifier"], str) and isinstance(m["applicationIdentifier"], str)
        assert m["midPointIdentifier"] in allowed_mid
        assert m["applicationIdentifier"] in allowed_app
