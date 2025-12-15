# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from pydantic import BaseModel, Field

from ...common.schema import ApplicationSchema


class BasicAttributeStats(BaseModel):
    """
    Basic statistics for an attribute computed on the MidPoint side.

    - totalCount: total number of records evaluated for this attribute
    - nuniq: number of unique, non-missing values
    - nmissing: number of missing (null/empty) values

    Percentages can be derived as nuniq/totalCount and nmissing/totalCount on the service side.
    """

    totalCount: int = Field(
        ...,
        ge=0,
        description="Total number of records considered for this attribute.",
    )
    nuniq: int = Field(
        ...,
        ge=0,
        description="Number of unique non-missing values for the attribute.",
    )
    nmissing: int = Field(
        ...,
        ge=0,
        description="Number of missing values for the attribute.",
    )


class SuggestExtensionRequest(BaseModel):
    """
    Input for suggesting correlation attributes from UNMAPPED application attributes.

    Pass into `applicationSchema.attribute` only those attributes that were NOT mapped
    during schema matching (i.e., candidates for 'extension').
    """

    applicationSchema: ApplicationSchema = Field(
        ...,
        description=(
            "Application schema with UNMAPPED attributes (candidates for extension). "
            "`name` and `description` are used as context; `attribute` is the input."
        ),
    )

    attributeStats: dict[str, BasicAttributeStats] = Field(
        ...,
        description=(
            "Mapping from attribute name to basic stats (totalCount, nuniq, nmissing) "
            "computed in midPoint. Used by the LLM to decide suitable extension attributes."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "applicationSchema": {
                        "name": "ri:account",
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
            ]
        }
    }


class SuggestExtensionResponse(BaseModel):
    """
    Output containing names of attributes proposed for MidPoint extension.
    The attributes are returned AS-IS from the LLM, i.e., using the resource
    attribute naming as provided in the input schema.
    """

    extensionAttributes: List[str] = Field(
        ...,
        description=(
            "List of resource attribute names returned as-is, e.g., "
            "c:attributes/ri:personalNumber, c:attributes/ri:department."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "extensionAttributes": [
                    "c:attributes/ri:personalNumber",
                    "c:attributes/ri:department",
                ]
            }
        }
    }
