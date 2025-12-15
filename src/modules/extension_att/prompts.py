# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel


class ExtensionAttributes(BaseModel):
    """Contains list of attribute names proposed for MidPoint extension (correlator-like)."""

    extensionAttributes: List[str]


template = """
You are given a Resource schema (name, description, and its attributes) and optional basic statistics
for each attribute. Your task is to propose which Resource attributes should be mapped into MidPoint
"extension" as interesting attributes. For now, consider "interesting" to mean attributes that would
make good correlators (e.g., primary keys or unique identifiers such as personal number, UID, etc.).

When deciding, consider:
- Semantic meaning from attribute names/descriptions.
- Type suitability for identifiers (e.g., string, integer, not multi-valued if such metadata is provided).
- Basic statistics if available: prefer attributes that are unique across records and have no/few missing values.

Additionally, you will receive basic statistics for each attribute:
- totalCount: total number of records considered
- nuniq: number of unique non-missing values
- nmissing: number of missing values
Use these statistics to prefer attributes that are unique across records and have no (or the fewest) missing values.

{format_instructions}

Provide output in JSON format. 
Comments are not allowed in JSON. 
Output only attribute names.
Do not make up new attributes.
Do not provide empty lists, empty strings, or null values.

Suggest extension (correlator-like) attributes for this Resource schema:
{Resource_schema}

Attribute statistics (may be empty if not provided):
{Attribute_stats}

""".strip()

parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=ExtensionAttributes)

prompt = PromptTemplate(
    template=template,
    input_variables=["Resource_schema", "Attribute_stats"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
