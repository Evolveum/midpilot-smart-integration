# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from pydantic import BaseModel, Field, field_validator

from ...common.schema import BaseSchemaAttribute


class AttributeValueCount(BaseModel):
    """
    Frequency count for one value of an application attribute.
    Maps to ShadowAttributeValueCountType on the Java side.
    """

    value: str = Field(..., description="The observed attribute value.")
    count: int = Field(..., description="Number of occurrences of this value.")


class SuggestCategoricalMappingRequest(BaseModel):
    """
    Request to suggest a categorical (enum-to-enum) inbound mapping script.
    Used when no correlated data pairs are available but the source attribute
    appears categorical (value count ~ MP enum count).
    Maps to SiSuggestCategoricalMappingRequestType on the Java side.
    """

    applicationAttribute: BaseSchemaAttribute = Field(..., description="Definition of the application-side attribute.")
    midPointAttribute: BaseSchemaAttribute = Field(
        ..., description="Definition of the midPoint-side categorical attribute."
    )
    inbound: bool = Field(..., description="Is the mapping to be produced an inbound one?")
    applicationAttributeValue: List[str] = Field(
        default_factory=list,
        description="List of observed values of the application attribute.",
    )
    midPointCategoryValue: List[str] = Field(
        default_factory=list,
        description="Known enum values of the midPoint categorical attribute (e.g. 'enabled', 'disabled', 'archived').",
    )

    @field_validator("inbound")
    @classmethod
    def validate_inbound(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Outbound categorical mapping is not yet supported")
        return v


class SuggestCategoricalMappingResponse(BaseModel):
    """
    The inferred Groovy code snippet that maps application categorical values to midPoint enum values.
    Shares the same shape as SuggestMappingResponse / SiSuggestMappingResponseType.
    """

    description: str = Field(
        ...,
        description="One-line description of the transformation. MUST match the first-line comment (after '// ') in transformationScript.",
    )
    transformationScript: str | None = Field(
        None,
        description="Groovy code starting with a single-line comment `// <description>` on the first line, followed by the mapping logic.",
    )
