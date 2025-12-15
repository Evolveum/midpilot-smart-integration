# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from pydantic import BaseModel, Field

# -------------------------
# Common types
# -------------------------


class AttributeValue(BaseModel):
    """Single attribute-value item within one record (instance)."""

    attribute: str = Field(..., description="Attribute path, e.g. 'c:email[*]/value'")
    value: List[str] = Field(..., description="List of values (single-valued => one item)")


class Record(BaseModel):
    """One record on a side, identified by a stable identifier."""

    identifier: str = Field(..., description="Opaque, side-local ID (e.g., '1', 'A1', 'M77').")
    content: List[AttributeValue] = Field(..., min_length=1, description="Attribute-value entries for this record.")


# -------------------------
# Request (pairs with lists of records per side)
# -------------------------


class Pair(BaseModel):
    """One aligned sample containing both sides (each side can contain 1..N records)."""

    midPoint: List[Record] = Field(..., description="List of MidPoint records (single or multiple).")
    application: List[Record] = Field(..., description="List of Application records (single or multiple).")


class ComplexPairingRequest(BaseModel):
    """Request payload for complex pairing matching across N aligned samples (pairs)."""

    pairs: List[Pair] = Field(
        default_factory=list,
        description="Aligned samples as pairs with `midPoint` and `application`, both being lists of records.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
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
                                    {"attribute": "c:contact/email[*]/address", "value": ["ANNA.NOVAKOVA@FIRMA.SK"]},
                                    {"attribute": "c:contact/email[*]/category", "value": ["work"]},
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
                            },
                            {
                                "identifier": "3",
                                "content": [
                                    {"attribute": "c:email[*]/value", "value": ["adam.kral@gmail.com"]},
                                    {"attribute": "c:email[*]/type", "value": ["personal"]},
                                ],
                            },
                        ],
                        "application": [
                            {
                                "identifier": "B1",
                                "content": [
                                    {"attribute": "c:contact/email[*]/address", "value": ["ADAM.KRAL4@STARTUP.IO"]},
                                    {"attribute": "c:contact/email[*]/category", "value": ["work"]},
                                ],
                            },
                            {
                                "identifier": "B2",
                                "content": [
                                    {"attribute": "c:contact/email[*]/address", "value": ["adam.kral@gmail.com"]},
                                    {"attribute": "c:contact/email[*]/category", "value": ["home"]},
                                ],
                            },
                        ],
                    },
                    {
                        "midPoint": [
                            {
                                "identifier": "4",
                                "content": [
                                    {"attribute": "c:email[*]/value", "value": ["jana.nova+sales@evolveum.com"]},
                                    {"attribute": "c:email[*]/type", "value": ["work"]},
                                ],
                            }
                        ],
                        "application": [
                            {
                                "identifier": "C7",
                                "content": [
                                    {"attribute": "c:contact/email[*]/address", "value": ["jana.nova@firma.sk"]},
                                    {"attribute": "c:contact/email[*]/category", "value": ["work"]},
                                ],
                            }
                        ],
                    },
                    {
                        "midPoint": [
                            {
                                "identifier": "5",
                                "content": [
                                    {"attribute": "c:email[*]/value", "value": ["marcela.nemcova30@gmail.com"]},
                                    {"attribute": "c:email[*]/type", "value": ["personal"]},
                                ],
                            },
                            {
                                "identifier": "6",
                                "content": [
                                    {"attribute": "c:email[*]/value", "value": ["marcela.nemcova77@gmail.com"]},
                                    {"attribute": "c:email[*]/type", "value": ["work"]},
                                ],
                            },
                        ],
                        "application": [
                            {
                                "identifier": "M30",
                                "content": [
                                    {
                                        "attribute": "c:contact/email[*]/address",
                                        "value": ["marcelanemcova30@gmail.com"],
                                    },
                                    {"attribute": "c:contact/email[*]/category", "value": ["home"]},
                                ],
                            },
                        ],
                    },
                    {
                        "midPoint": [
                            {
                                "identifier": "7",
                                "content": [
                                    {"attribute": "c:email[*]/value", "value": ["kontakt@spolocnost.sk"]},
                                    {"attribute": "c:email[*]/type", "value": ["work"]},
                                ],
                            }
                        ],
                        "application": [
                            {
                                "identifier": "K1",
                                "content": [
                                    {"attribute": "c:contact/email[*]/address", "value": ["KONTAKT@SPOLOCNOST.SK"]},
                                    {"attribute": "c:contact/email[*]/category", "value": ["work"]},
                                ],
                            }
                        ],
                    },
                ]
            }
        }
    }


# -------------------------
# Response (identifier ↔ identifier)
# -------------------------


class IdMapping(BaseModel):
    """Mapping from one midPoint record ID to one Application record ID."""

    midPointIdentifier: str = Field(..., description="Identifier from the MidPoint side.", alias="midPointIdentifier")
    applicationIdentifier: str = Field(
        ..., description="Identifier from the Application side.", alias="applicationIdentifier"
    )


class ComplexPairingResponse(BaseModel):
    """Verdict (similar), rationale, and minimalist identifier-to-identifier mappings for complex pairing."""

    similar: bool = Field(..., description="True if a strict majority (>50%) of non-empty samples match.")
    rationale: str = Field(..., min_length=1, description="Short explanation for the decision.")
    mappings: List[IdMapping] = Field(
        ..., min_length=1, description="Resolved identifier pairs MidPoint -> Application."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "similar": True,
                "rationale": "4 out of 5 pairs have matching records based on email normalization and category synonymy (work≈business, personal≈home)",
                "mappings": [
                    {"midPointIdentifier": "1", "applicationIdentifier": "A1"},
                    {"midPointIdentifier": "2", "applicationIdentifier": "B1"},
                    {"midPointIdentifier": "3", "applicationIdentifier": "B2"},
                    {"midPointIdentifier": "4", "applicationIdentifier": "C7"},
                    {"midPointIdentifier": "5", "applicationIdentifier": "M30"},
                    {"midPointIdentifier": "7", "applicationIdentifier": "K1"},
                ],
            }
        }
    }
