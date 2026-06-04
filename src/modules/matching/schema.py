# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from pydantic import BaseModel, Field

from ...common.schema import ApplicationSchema, MidpointSchema
from .schema_examples import (
    midpoint_email_address_description_example,
    midpoint_name_description_example,
    midpoint_organizational_unit_description_example,
    midpoint_schema_description_example,
    midpoint_telephone_number_description_example,
)


class MatchSchemaRequest(BaseModel):
    """
    Request schema for suggesting attribute matching.
    """

    applicationSchema: ApplicationSchema = Field(..., description="Application schema with metadata and attributes.")
    midPointSchema: MidpointSchema = Field(..., description="Midpoint schema with metadata and attributes.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "applicationSchema": {
                        "name": "ri:account",
                        "attribute": [
                            {"name": "c:attributes/ri:phone", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                            {
                                "name": "c:attributes/ri:department",
                                "type": "xsd:string",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
                            {
                                "name": "c:attributes/ri:personalNumber",
                                "type": "xsd:string",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
                            {"name": "c:attributes/ri:email", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                            {"name": "c:attributes/ri:created", "type": "xsd:dateTime", "minOccurs": 0, "maxOccurs": 1},
                            {"name": "c:attributes/icfs:name", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                            {
                                "name": "c:attributes/ri:lastLogin",
                                "type": "xsd:dateTime",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
                            {"name": "c:attributes/icfs:uid", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                            {
                                "name": "c:credentials/c:password/c:value",
                                "type": "t:ProtectedStringType",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
                            {
                                "name": "c:activation/c:administrativeStatus",
                                "type": "c:ActivationStatusType",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
                        ],
                    },
                    "midPointSchema": {
                        "name": "c:UserType",
                        "description": midpoint_schema_description_example,
                        "attribute": [
                            {
                                "name": "c:name",
                                "type": "xsd:string",
                                "description": midpoint_name_description_example,
                                "minOccurs": 0,
                                "maxOccurs": 0,
                            },
                            {
                                "name": "c:emailAddress",
                                "type": "xsd:string",
                                "description": midpoint_email_address_description_example,
                                "minOccurs": 0,
                                "maxOccurs": 0,
                            },
                            {
                                "name": "c:telephoneNumber",
                                "type": "xsd:string",
                                "description": midpoint_telephone_number_description_example,
                                "minOccurs": 0,
                                "maxOccurs": 0,
                            },
                            {
                                "name": "c:organizationalUnit",
                                "type": "xsd:string",
                                "description": midpoint_organizational_unit_description_example,
                                "minOccurs": 0,
                                "maxOccurs": 0,
                            },
                        ],
                    },
                }
            ]
        }
    }


class SchemaAttributeMatch(BaseModel):
    """
    Schema representing one particular match of MidPoint and Application attribute.
    Note that for each attribute there may exist multiple matches.
    """

    midPointAttribute: str = Field(..., description="MidPoint attribute name")
    applicationAttribute: str = Field(..., description="Application attribute name")


class MatchSchemaResponse(BaseModel):
    """
    Response schema for suggesting attribute matching.
    """

    attributeMatch: List[SchemaAttributeMatch] = Field(..., description="List of matched schema attributes")
