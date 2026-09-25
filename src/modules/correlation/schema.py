# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ...common.schema import BaseSchemaAttribute, ResponseMetadata, get_response_metadata


class BasicAttributeStats(BaseModel):
    """
    Basic statistics for an attribute computed on the midPoint side.
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


class SuggestExtensionCorrelatorsRequest(BaseModel):
    """
    Input for suggesting correlation attributes from midPoint extension attributes.
    Provide midPoint schema context and the list of extension attributes.
    """

    schemaName: str = Field(..., description="MidPoint schema name.")
    schemaDescription: Optional[str] = Field(None, description="Optional description of the midPoint schema.")
    extensionAttributes: List[BaseSchemaAttribute] = Field(
        ...,
        description="MidPoint extension attributes (e.g., extension/ext:personalNumber) considered for correlation.",
    )
    attributeStats: Dict[str, BasicAttributeStats] = Field(
        ...,
        description="Mapping from attribute name to basic stats (totalCount, nuniq, nmissing) computed in midPoint.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "schemaName": "Employee",
                "schemaDescription": "Employee object type with HR-driven extensions.",
                "extensionAttributes": [
                    {
                        "name": "extension/ext:personalNumber",
                        "type": "xsd:string",
                        "description": "Unique personal number assigned by HR.",
                        "minOccurs": 0,
                        "maxOccurs": 1,
                    },
                    {
                        "name": "extension/ext:email",
                        "type": "xsd:string",
                        "description": "Corporate email address.",
                        "minOccurs": 0,
                        "maxOccurs": 1,
                    },
                    {
                        "name": "extension/ext:phone",
                        "type": "xsd:string",
                        "description": "Phone number with optional country code.",
                        "minOccurs": 0,
                        "maxOccurs": 1,
                    },
                ],
                "attributeStats": {
                    "extension/ext:personalNumber": {"totalCount": 10000, "nuniq": 9950, "nmissing": 50},
                    "extension/ext:email": {"totalCount": 10000, "nuniq": 9800, "nmissing": 200},
                    "extension/ext:phone": {"totalCount": 10000, "nuniq": 8500, "nmissing": 1500},
                },
            }
        }
    }


class SuggestExtensionCorrelatorsResponse(BaseModel):
    """
    Output: only a list of attribute names proposed for correlation.
    """

    correlators: List[str] = Field(
        ...,
        description="List of attribute names proposed for correlators (e.g., extension/ext:personalNumber).",
    )
    metadata: ResponseMetadata = Field(
        default_factory=get_response_metadata,
        description="Metadata about configured provider and used model.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "correlators": [
                    "extension/ext:personalNumber",
                    "extension/ext:email",
                ]
            }
        }
    }
