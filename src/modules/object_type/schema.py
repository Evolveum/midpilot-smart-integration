# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from src.common.schema import ApplicationSchema


class PatternTypeEnum(str, Enum):
    """
    Enum representing different types of string pattern matching strategies.

    Attributes:
        PREFIX: - content starts with one of these values: "prod", "priv", "adm", "usr", "user", "ops", "svc", "int", "ext"
                - no delimiter needed
        SUFFIX: - content ends with one of these values: "prod", "priv", "adm", "admin", "administrator", "usr", "user", "ops", "svc", "int", "ext"
                - no delimiter needed
        FIRST_TOKEN: - content is split into tokens on non-alphanumeric characters and the first token is counted
                     - taken into account only if cardinality is lower than 0.05 * total number of samples
                     - delimiter needed
        LAST_TOKEN: - content is split into tokens on non-alphanumeric characters and the last token is counted
                    - taken into account only if cardinality is lower than 0.05 * total number of samples
                    - delimiter needed
        DN_SUFFIX: - LDAP's DN attribute is processed in a specific way
                   - suffix starting from first 'ou' is counted as value pattern
                   - 'ou' delimiter needed
    """

    PREFIX = "prefix"
    SUFFIX = "suffix"
    FIRST_TOKEN = "firstToken"
    LAST_TOKEN = "lastToken"
    DN_SUFFIX = "DNsuffix"


class PatternCountStat(BaseModel):
    """
    Frequency count for one pattern value in raw MidPoint stats.
    """

    value: str = Field(..., description="The observed pattern value.")
    type: PatternTypeEnum = Field(..., description="The type of the pattern value.")
    count: int = Field(..., description="Number of occurrences of this value.")


class ValueCountStat(BaseModel):
    """
    Frequency count for one attribute value in raw MidPoint stats.
    """

    value: str = Field(..., description="The observed attribute value.")
    count: int = Field(..., description="Number of occurrences of this value.")


class AttributeStat(BaseModel):
    """
    Raw MidPoint attribute statistics (unique, missing, and value counts).
    """

    ref: str = Field(..., description="Attribute reference or name.")
    uniqueValueCount: int = Field(..., description="Number of unique values.")
    missingValueCount: int = Field(..., description="Number of missing values.")
    valueCount: Optional[List[ValueCountStat]] = Field(
        None, description="Optional frequency counts for values (for top-N)."
    )
    valuePatternCount: Optional[List[PatternCountStat]] = Field(
        None, description="Optional frequency counts for value patterns (if presented in data)."
    )


class TupleValueCount(BaseModel):
    """
    Statistic for a pair of values in a tuple count.
    """

    value: Tuple[str, str] = Field(..., description="The pair of values for two attributes.")
    count: int = Field(..., description="Number of occurrences of this value pair.")


class AttributeTupleStat(BaseModel):
    """
    Raw MidPoint tuple statistics for attribute pairs.
    """

    ref: Tuple[str, str] = Field(..., description="Names of the two low-cardinality attributes.")
    tupleCount: Optional[List[TupleValueCount]] = Field(None, description="Counts of value pairs in this cross-table.")


class Statistics(BaseModel):
    """
    Standardized statistics model for object-type prompting or raw MidPoint stats.
    """

    attribute: List[AttributeStat] = Field(..., description="List of attribute statistics.")
    attributeTuple: Optional[List[AttributeTupleStat]] = Field(
        None, description="Optional cross-attribute tuple statistics."
    )
    size: int = Field(..., description="Total number of records.")
    coverage: float = Field(..., description="Proportion of records covered (0.0–1.0).")
    timestamp: Optional[str] = Field(None, description="ISO timestamp when statistics were computed.")


class SuggestObjectTypeRequest(BaseModel):
    """
    Request payload for suggesting object types based on schema and statistics.
    Optionally includes structured validationErrorFeedback from backend to guide a corrective retry.
    """

    model_config = ConfigDict(
        validate_by_name=True,
        json_schema_extra={
            "example": {
                "schema": {
                    "name": "ri:group",
                    "description": "Contains group entries",
                    "attribute": [
                        {"name": "c:attributes/ri:loginShell", "type": "xsd:string", "minOccurs": 1, "maxOccurs": 1},
                        {"name": "c:attributes/ri:groupType", "type": "xsd:double", "minOccurs": 1, "maxOccurs": 1},
                        {
                            "name": "c:activation/c:administrativeStatus",
                            "type": "xsd:string",
                            "minOccurs": 0,
                            "maxOccurs": 1,
                        },
                        {
                            "name": "c:credentials/c:password/c:value",
                            "type": "xsd:string",
                            "minOccurs": 0,
                            "maxOccurs": 1,
                        },
                        {
                            "name": "c:attributes/c=ri:dn",
                            "type": "xsd:string",
                            "minOccurs": 1,
                            "maxOccurs": 1,
                            "description": "Distinguished Name (DN)",
                        },
                    ],
                },
                "statistics": {
                    "attribute": [
                        {
                            "ref": "c:attributes/ri:groupType",
                            "uniqueValueCount": 4,
                            "missingValueCount": 0,
                            "valueCount": [
                                {"value": "-2147483646.0", "count": 1395},
                                {"value": "8.0", "count": 238},
                            ],
                        },
                        {
                            "ref": "c:attributes/ri:dn",
                            "uniqueValueCount": 1670,
                            "missingValueCount": 0,
                            "valuePatternCount": [
                                {"value": "ou=Groups,dc=example,dc=com", "type": "DNsuffix", "count": 1633},
                                {"value": "ou=Service,dc=example,dc=com", "type": "DNsuffix", "count": 37},
                            ],
                        },
                    ],
                    "attributeTuple": [
                        {
                            "ref": ["c:attributes/ri:loginShell", "c:activation/c:administrativeStatus"],
                            "tupleCount": [
                                {"value": ["true", "active"], "count": 872},
                                {"value": ["false", "frozen"], "count": 828},
                            ],
                        },
                    ],
                    "size": 1670,
                    "coverage": 1,
                },
                "validationErrorFeedback": [
                    {
                        "objectType": {
                            "kind": "entitlement",
                            "intent": "security",
                            "displayName": "Security Entitlement",
                            "description": "…",
                            "filter": ["c:attributes/ri:groupType = -2147483646.0"],
                        },
                        "filterErrors": ["Unknown attribute ri:groupType"],
                    }
                ],
            }
        },
    )

    applicationSchema: ApplicationSchema = Field(
        ..., alias="schema", description="MidPoint application schema for the target object class."
    )
    statistics: Statistics = Field(..., description="Computed statistics for the target object class.")
    validationErrorFeedback: Optional[List["ValidationErrorFeedbackEntry"]] = Field(
        default=None,
        alias="validationErrorFeedback",
        description="Optional structured feedback entries for previously suggested object types; each includes the problematic suggestion and human-readable filter error messages.",
    )


class ObjectTypeSuggestion(BaseModel):
    """
    One suggested object type delineation from the LLM.
    """

    kind: str = Field(..., description="One of 'account', 'entitlement', or 'generic'.")
    intent: str = Field(..., description="Usage context, e.g. 'admin', 'default'.")
    displayName: str = Field(..., description="A user-friendly name representing the combination of kind and intent")
    description: str = Field(..., description="A detailed explanation describing the chosen delineation")
    filter: Optional[List[str]] = Field(None, description="List of MQL/MGL filter expressions.")
    baseContextFilter: Optional[str] = Field(None, description="Base context filter expression.")
    baseContextObjectClassName: Optional[str] = Field(
        None,
        description="Name of the base context object class, typically 'ri:organizationalUnit' when baseContextFilter is present.",
    )

    def model_post_init(self, __context):
        # Set baseContextObjectClassName to "organizationalUnit" when baseContextFilter is present
        if self.baseContextFilter is not None and self.baseContextObjectClassName is None:
            self.baseContextObjectClassName = "organizationalUnit"


class ValidationErrorFeedbackEntry(BaseModel):
    """
    Feedback entry describing issues detected when applying or validating one object type.
    Carries the problematic suggestion and a list of human‑readable error messages related to its filters.
    Mirrors SiValidationErrorFeedbackEntryType from BE schema.
    """

    objectType: ObjectTypeSuggestion = Field(..., description="Suggested object type that failed validation.")
    filterErrors: Optional[List[str]] = Field(
        default=None,
        description="Human-readable error messages encountered while parsing, compiling, or evaluating the delineation filter for the associated suggestion.",
    )


class SuggestObjectTypeResponse(BaseModel):
    """
    Response payload containing suggested object types.
    """

    model_config = ConfigDict(
        validate_by_name=True,
        json_schema_extra={
            "example": {
                "objectType": [
                    {
                        "kind": "entitlement",
                        "intent": "security",
                        "displayName": "Security Entitlement",
                        "description": "Grants or restricts access to security-related features, permissions, or resources within the system. This entitlement determines a user's or application's authorization to perform specific security-sensitive actions.",
                        "filter": ["c:attributes/ri:groupType = -2147483646.0"],
                    },
                    {
                        "kind": "entitlement",
                        "intent": "distribution",
                        "displayName": "Entitlement Distribution",
                        "description": "Manages the allocation and delivery of entitlements (such as rights, access, or benefits) to designated recipients.",
                        "filter": ["c:attributes/ri:groupType = 8.0"],
                    },
                    {
                        "kind": "generic",
                        "intent": "organizationalUnitSubset",
                        "displayName": "Organizational Unit (Projects Base Context)",
                        "description": "Objects under the LDAP organizational unit 'projects' base context. Uses baseContextFilter on dn to scope the dataset.",
                        "baseContextFilter": "c:attributes/ri:dn = ou=projects,dc=example,dc=com",
                    },
                ]
            }
        },
    )

    objectType: List[ObjectTypeSuggestion] = Field(..., description="Suggested object types.")
