# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, BeforeValidator, Field

from src.config import config
from src.modules.utils import clean_description
from src.utils import strip_common_prefix

# A string field that silently normalizes legacy 'c:'-prefixed item paths/names
# (e.g. 'c:attributes/ri:emptype' -> 'attributes/ri:emptype', 'c:UserType' -> 'UserType').
# Works as dict key, list element and tuple member as well.
NormalizedPath = Annotated[str, BeforeValidator(strip_common_prefix)]


class ResponseMetadata(BaseModel):
    """
    Metadata about configured AI inference provider and model.
    """

    provider: str = Field(..., description="Configured inference provider.")
    model: str = Field(..., description="Configured model identifier.")


def get_response_metadata() -> ResponseMetadata:
    """
    Return ResponseMetadata instance with configured provider and model.
    """
    return ResponseMetadata(provider=config.llm.openai_api_base, model=config.llm.model_name)


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

    name: NormalizedPath = Field(..., description="The attribute's name.")
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

    name: NormalizedPath = Field(..., description="The name of the schema or entity (e.g., 'account').")
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

    UserType = "UserType"
    RoleType = "RoleType"
    OrgType = "OrgType"
    ServiceType = "ServiceType"


class MidpointSchema(BaseSchema):
    """
    Represents the Midpoint schema with metadata and attributes.
    """

    name: Annotated[FocusType, BeforeValidator(strip_common_prefix)] = Field(
        ..., description="Name of Midpoint schema always represents a focus type."
    )
