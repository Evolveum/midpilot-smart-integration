# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from unittest.mock import patch

import pytest

from src.modules.complex_pairing import service as svc
from src.modules.complex_pairing.schema import AttributeValue, ComplexPairingRequest, Pair, Record
from test.unit.modules.utils import response_mock

# ---------- Helper tests: _pairs_json ----------


def test_pairs_json_builds_expected_structure():
    req = ComplexPairingRequest(
        pairs=[
            Pair(
                midPoint=[
                    Record(
                        identifier="1",
                        content=[
                            AttributeValue(attribute="c:email[*]/value", value=["anna@example.com"]),
                            AttributeValue(attribute="c:email[*]/type", value=["work"]),
                        ],
                    )
                ],
                application=[
                    Record(
                        identifier="A1",
                        content=[
                            AttributeValue(attribute="c:contact/email/address", value=["ANNA@EXAMPLE.COM"]),
                            AttributeValue(attribute="c:contact/email/category", value=["work"]),
                        ],
                    )
                ],
            ),
            Pair(
                midPoint=[
                    Record(
                        identifier="2",
                        content=[AttributeValue(attribute="c:email[*]/value", value=["bob@example.com"])],
                    )
                ],
                application=[
                    Record(
                        identifier="B1",
                        content=[AttributeValue(attribute="c:contact/email/address", value=["BOB@EXAMPLE.COM"])],
                    )
                ],
            ),
        ]
    )

    pairs = svc._pairs_json(req)
    assert isinstance(pairs, list) and len(pairs) == 2

    first = pairs[0]
    assert set(first.keys()) == {"midPoint", "application"}
    assert isinstance(first["midPoint"], list) and isinstance(first["application"], list)
    mp0 = first["midPoint"][0]
    app0 = first["application"][0]
    assert mp0["identifier"] == "1" and app0["identifier"] == "A1"
    assert isinstance(mp0["content"], list) and isinstance(app0["content"], list)
    assert mp0["content"][0]["attribute"] == "c:email[*]/value"
    assert mp0["content"][0]["value"] == ["anna@example.com"]


# ---------- Main flow tests: complex_pairing ----------


@pytest.mark.asyncio
@patch(
    "src.modules.complex_pairing.service.get_default_llm",
    response_mock(
        json.dumps(
            {
                "similar": True,
                "rationale": "Most samples are matching based on normalized emails and categories.",
                "mappings": [
                    {"midPointIdentifier": "1", "applicationIdentifier": "A1"},
                    {"midPointIdentifier": "2", "applicationIdentifier": "B1"},
                ],
            }
        )
    ),
)
async def test_complex_pairing_parses_llm_output():
    req = ComplexPairingRequest(
        pairs=[
            Pair(
                midPoint=[
                    Record(
                        identifier="1",
                        content=[
                            AttributeValue(attribute="c:email[*]/value", value=["anna@example.com"]),
                            AttributeValue(attribute="c:email[*]/type", value=["work"]),
                        ],
                    )
                ],
                application=[
                    Record(
                        identifier="A1",
                        content=[
                            AttributeValue(attribute="c:contact/email/address", value=["ANNA@EXAMPLE.COM"]),
                            AttributeValue(attribute="c:contact/email/category", value=["work"]),
                        ],
                    )
                ],
            )
        ]
    )

    resp = await svc.complex_pairing(req)

    assert resp.similar is True
    assert isinstance(resp.rationale, str) and resp.rationale.strip() != ""
    assert resp.mappings and len(resp.mappings) == 2
    assert resp.mappings[0].midPointIdentifier == "1"
    assert resp.mappings[0].applicationIdentifier == "A1"
