# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ----- Output schema -----


class IdMapping(BaseModel):
    midPointIdentifier: str = Field(..., description="Identifier from the MidPoint side", alias="midPointIdentifier")
    applicationIdentifier: str = Field(
        ..., description="Identifier from the Application side", alias="applicationIdentifier"
    )


class ComplexPairingResponse(BaseModel):
    similar: bool = Field(..., description="Strict majority (>50%) of considered samples match")
    rationale: str = Field(..., min_length=1, description="One short sentence explaining the decision")
    mappings: List[IdMapping] = Field(..., description="Identifier pairs MidPoint -> Application")


parser: PydanticOutputParser[ComplexPairingResponse] = PydanticOutputParser(pydantic_object=ComplexPairingResponse)
FORMAT = parser.get_format_instructions()

SYSTEM_TMPL = """
You are a careful data-matching judge.

GOAL
- Decide if midPoint and application sides are overall similar (strict majority).
- Return only identifier-to-identifier mappings for records that correspond.
- Do NOT echo or restate the input; output must contain ONLY the fields defined by the schema.

INPUT FORMAT
- pairs_json: array of pairs; each pair has:
  { "midPoint": [ { "identifier": "...",
                    "content": [ {"attribute":"...", "value":[...]} , ... ] }, ... ],
    "application": [ { "identifier": "...",
                       "content": [ {"attribute":"...", "value":[...]} , ... ] }, ... ] }
- Each side is a list (single- or multi-record). Identifiers are opaque and side-local.

MATCHING RULES (value-aware, benevolent)
- Normalize only for decisions (case/diacritics-insensitive; Gmail-style: ignore dots and plus-tags; trim spaces).
- Same KIND matches: email↔email, phone↔phone, url↔url, address↔address. Cross-kind = no match.
- Categories synonyms (case-insensitive): home≈personal≈private; work≈business≈company≈office≈job; mobile≈cell.
- Within one pair, produce one-to-one matches; do not force mismatches.
- A sample counts as MATCHING if a majority of its evaluated value-edges score ≥1 (same-kind or better).
- similar = TRUE iff a strict majority of considered samples are MATCHING.

OUTPUT (STRICT)
{{FORMAT}}

IMPORTANT: You MUST include a 'rationale' field that explains your decision in one or two sentences.

POLICY
- Do NOT include any keys beyond the schema.
- Do NOT include raw attribute values in the output.
- If nothing matches, return an empty mappings list with a clear rationale and similar=false.
- The response MUST include the 'rationale' field with a non-empty string value.
""".strip()

USER_TMPL = """pairs_json:
```json
{{ pairs_json }}
```
"""

system_msg = SystemMessagePromptTemplate.from_template(SYSTEM_TMPL, template_format="jinja2")
user_msg = HumanMessagePromptTemplate.from_template(USER_TMPL, template_format="jinja2")
prompt_all = ChatPromptTemplate.from_messages([system_msg, user_msg]).partial(FORMAT=FORMAT)
