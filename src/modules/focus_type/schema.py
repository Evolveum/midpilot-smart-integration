# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from ...common.schema import ApplicationSchema


class FocusType(str, Enum):
    """
    Enum of possible focus types without namespace prefix.
    Used for LLM output and internal processing.
    """

    UserType = "UserType"
    RoleType = "RoleType"
    OrgType = "OrgType"
    ServiceType = "ServiceType"


class SuggestFocusTypeRequest(BaseModel):
    """
    Request schema for suggesting a focus type.
    """

    kind: str = Field(..., description="The entity kind for which to suggest a focus type.")
    intent: str = Field(..., description="The context or intent guiding the suggestion.")
    baseContextFilter: Optional[str] = Field(None, description="Optional base context filter.")
    applicationSchema: ApplicationSchema = Field(..., alias="schema", description="The application schema object.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "kind": "account",
                    "intent": "default",
                    "baseContextFilter": "attributes/name = 'main'",
                    "schema": {
                        "name": "ri:account",
                        "description": "Contains user accounts",
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
                            {"name": "c:attributes/ri:status", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                            {
                                "name": "c:attributes/ri:description",
                                "type": "xsd:string",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
                            {"name": "c:attributes/icfs:name", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                            {"name": "c:attributes/ri:type", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1},
                            {
                                "name": "c:attributes/ri:fullname",
                                "type": "xsd:string",
                                "description": "User's full name",
                                "minOccurs": 1,
                                "maxOccurs": 1,
                            },
                            {
                                "name": "c:attributes/ri:lastLogin",
                                "type": "xsd:dateTime",
                                "minOccurs": 0,
                                "maxOccurs": 1,
                            },
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
            ]
        }
    }


class SuggestFocusTypeResponse(BaseModel):
    """
    Response schema containing the suggested focus type name.
    """

    focusTypeName: FocusType = Field(..., description="Suggested focus type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"focusTypeName": "UserType"},
            ]
        }
    }
