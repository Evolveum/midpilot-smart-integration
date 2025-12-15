# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from .schema import SuggestExtensionCorrelatorsResponse

parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=SuggestExtensionCorrelatorsResponse)


template = """
Act as a MidPoint correlation advisor.
Your task is to select extension attributes that are suitable for correlation.

Context about the MidPoint schema:
- Name: {schema_name}
- Description: {schema_description}

Candidate MidPoint extension attributes (Python dictionary list):
{extension_attributes}

Basic statistics for attributes (JSON mapping name -> stats):
{attributeStats}

Guidelines:
- Prefer attributes with high uniqueness (nuniq close to totalCount) and low missing rate (nmissing close to 0).
- Use only attribute names that appear in the provided extension attributes.
- If none are suitable, return an empty list.

{format_instructions}

Provide output strictly in JSON format with no comments.
""".strip()


prompt = PromptTemplate(
    template=template,
    input_variables=["schema_name", "schema_description", "extension_attributes", "attributeStats"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
