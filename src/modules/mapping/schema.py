# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ...common.schema import BaseSchemaAttribute


# Allowed simple xsd types for clarity / validation
class SupportedDataType(str, Enum):
    XSD_STRING = "xsd:string"
    XSD_BOOLEAN = "xsd:boolean"
    XSD_INT = "xsd:int"
    XSD_LONG = "xsd:long"
    XSD_DOUBLE = "xsd:double"
    XSD_FLOAT = "xsd:float"
    XSD_DATETIME = "xsd:dateTime"


class MappingSchemaAttribute(BaseSchemaAttribute):
    type: SupportedDataType = Field(..., description="Restricted to SupportedDataType for this module")


class ValueExample(BaseModel):
    """
    A single attribute-value pair in an I/O example.

    A value is considered **missing** in an IOExample when EITHER:
        1) the attribute is absent from the `application` / `midPoint` list, OR
        2) the attribute is present but its `value` list is empty (`[]`).
    """

    name: str = Field(..., description="Name of the attribute")
    value: Optional[List[str]] = Field(None, description="List of values for this attribute")


class IOExample(BaseModel):
    """
    Examples of how the application attribute value maps to the midpoint attribute value.

    Each `application` and `midPoint` is a list of ValueExample items.
    """

    application: Optional[List[ValueExample]] = Field(
        None, description="List of attribute-value pairs as they appear in the application record"
    )
    midPoint: Optional[List[ValueExample]] = Field(
        None, description="List of attribute-value pairs as desired in the midpoint record"
    )


class SuggestMappingRequest(BaseModel):
    """
    One mapping job: attributes list and a handful of I/O examples.
    """

    applicationAttribute: List[MappingSchemaAttribute] = Field(
        ..., description="List of application-side attributes to map."
    )
    midPointAttribute: List[MappingSchemaAttribute] = Field(..., description="List of midpoint-side attributes to map.")
    inbound: bool = Field(..., description="Is the mapping to be produced an inbound one?")
    example: List[IOExample] = Field(..., description="Several (application -> midPoint) examples for inference.")

    errorLog: Optional[str] = Field(
        default=None,
        alias="errorLog",
        description="Optional backend validation error log from a previous attempt; when present, the LLM will use it to correct its output.",
    )

    previousScript: Optional[str] = Field(
        default=None,
        alias="previousScript",
        description="Optional: Groovy transformation script from the previous attempt that produced the errorLog.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "applicationAttribute": [
                    {"name": "c:attributes/icfs:name", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1}
                ],
                "midPointAttribute": [{"name": "c:name", "type": "xsd:string", "minOccurs": 0, "maxOccurs": 1}],
                "inbound": True,
                "example": [
                    {
                        "application": [{"name": "c:attributes/icfs:name", "value": ["jack"]}],
                        "midPoint": [{"name": "c:name", "value": ["JACK"]}],
                    },
                    {
                        "application": [{"name": "c:attributes/icfs:name", "value": ["jim"]}],
                        "midPoint": [{"name": "c:name", "value": ["JIM"]}],
                    },
                    {
                        "midPoint": [{"name": "c:name", "value": ["empty"]}],
                    },
                ],
                "errorLog": "Optional: Backend validation error log from previous attempt.",
                "previousScript": "// Uppercase input\n(input instanceof String ? input.toUpperCase() : null)",
            }
        }
    }


class SuggestMappingResponse(BaseModel):
    """
    The inferred Groovy code snippet that transforms applicationValue into midpointValue.
    """

    description: str = Field(
        ...,
        description="One-line description of the transformation. MUST match the first-line comment (after '// ') in transformationScript.",
    )
    transformationScript: str = Field(
        ...,
        description="Groovy code starting with a single-line comment `// <description>` on the first line, followed by the code. The last expression must evaluate to the desired value.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Uppercase input",
                "transformationScript": "// Uppercase input\n(input instanceof String ? input.toUpperCase() : null)",
            }
        }
    )
