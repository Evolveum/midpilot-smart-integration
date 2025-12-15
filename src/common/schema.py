# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from src.modules.utils import clean_description


class BaseSchemaAttribute(BaseModel):
    """
    Represents an attribute in the schema.

    Occurrence semantics
    --------------------
    - minOccurs: Minimum number of values (usually 0 or 1). 0 = optional, 1 = required.
    - maxOccurs: Maximum number of values (usually 1 or -1). 1 = single-valued, -1 = unbounded (unlimited).

    Allowed combinations (minOccurs, maxOccurs):
      - [0, 1]  → single optional
      - [1, 1]  → single required
      - [0, -1] → multi optional
      - [1, -1] → multi required
    """

    name: str = Field(..., description="The attribute's name.")
    type: str = Field(..., description="The attribute's data type (e.g., 'xsd:string').")
    description: Optional[str] = Field(
        None,
        description="Optional human-readable description of the attribute. May contain xml and html tags.",
    )
    minOccurs: int = Field(
        ...,
        description="Optional minimum number of occurrences of this attribute.",
    )
    maxOccurs: int = Field(
        ...,
        description="Optional maximum number of occurrences of this attribute.",
    )

    def model_post_init(self, __context):
        if self.description:
            self.description = clean_description(self.description)


class BaseSchema(BaseModel):
    """
    Represents the overall schema with metadata and attributes.
    """

    name: str = Field(..., description="The name of the schema or entity (e.g., 'account').")
    description: Optional[str] = Field(
        None, description="Optional human-readable description of the schema. May contain xml and html tags."
    )
    attribute: List[BaseSchemaAttribute] = Field(..., description="List of schema attributes.")

    def model_post_init(self, __context):
        if self.description:
            self.description = clean_description(self.description)


class ApplicationSchema(BaseSchema):
    """
    Represents the overall application schema with metadata and attributes.
    """

    pass


class FocusType(str, Enum):
    """
    Enumeration of possible focus types for suggestions.
    """

    UserType = "c:UserType"
    RoleType = "c:RoleType"
    OrgType = "c:OrgType"
    ServiceType = "c:ServiceType"


class MidpointSchema(BaseSchema):
    """
    Represents the Midpoint schema with metadata and attributes.
    """

    name: FocusType = Field(..., description="Name of Midpoint schema always represents a focus type.")
