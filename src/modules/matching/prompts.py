# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class Pair(BaseModel):
    """One MidPoint-Resource pair"""

    MidPoint: str = Field(..., description="Attribute from MidPoint schema.")
    Resource: List[str] = Field(..., description="List of matching attributes from Resource schema.")


class Pairs(BaseModel):
    """All matched MidPoint-Resource pairs in JSON format."""

    pairs: List[Pair]


parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Pairs)


template = """
Act as a schema matcher for relational schemas. 
Your task is to create semantic matches that specify how the elements of the Resource schema semantically correspond to the elements of the MidPoint schema. 
You can provide multiple matches for one MidPoint attribute.

These are the attributes of the MidPoint schema together with their descriptions (in Python dictionary format): 
```json
{MidPoint_schema}
```

These are the attributes of the Resource schema together with their descriptions (in Python dictionary format): 
```json
{Resource_schema}
```

{format_instructions}

IMPORTANT: `name` is a special attribute in midPoint, it is usually human-readable identifier of identity, always suggest mappings like `name` to `login`, or `name` to email address!

Provide output in JSON format. 
Comments are not allowed in JSON. 
Do not make up new attributes in schemas. 
Do not provide empty lists, empty strings, or null values.""".strip()

prompt = PromptTemplate(
    template=template,
    input_variables=["MidPoint_schema", "Resource_schema"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
