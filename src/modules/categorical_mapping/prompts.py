# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain_core.prompts import ChatPromptTemplate

suggest_categorical_mapping_system_prompt = """
You generate a Groovy value-mapping script for identity management.

You are given:
1. The VALUE DISTRIBUTION of an application attribute — a list of (value, count) pairs sorted by frequency.
2. The KNOWN ENUM VALUES of a midPoint categorical attribute (e.g. activation/administrativeStatus). **These are the final, exact values — use them as-is without any transformations or safety checks.**

Your task is to produce a Groovy script that maps each observed application value to the most semantically appropriate midPoint enum string value.

#### Rules

1. Use a `switch` statement — value-to-value mapping is correct and expected here.
2. The input variable is always named `input`.
3. For each application value, determine the best matching midPoint enum value based on semantic similarity (e.g. "1"/"true"/"active"/"enabled" → "enabled"; "0"/"false"/"inactive"/"disabled" → "disabled"; "deleted"/"archived" → "archived").
4. If an application value cannot be confidently mapped to any midPoint enum value, omit it.
5. The default case (unrecognized value) must return `null` — return `null` if input is null or blank.
6. Do not include any safety checks.
7. The script must start with exactly one single-line Groovy comment describing the transformation (e.g. `// Map status values to activation/administrativeStatus`). No other comments are allowed. Do not use path prefixes (e.g. c:, ri:) in description.

#### Output format (MANDATORY)
Return **exactly one JSON object** with this shape (escape newlines as `\\n` inside the string):

{{
  "description": "One-line description",
  "transformationScript": "// <same-one-line-description>\\n<Groovy code>"
}}

**Do not** include Markdown/code fences, language tags, XML/HTML tags, extra keys, or surrounding text. The JSON must be syntactically valid.
""".strip()

suggest_categorical_mapping_human_prompt = """
Application attribute: {app_attr_name} ({app_attr_type})
MidPoint attribute: {mp_attr_name}

Application value distribution (value -> count, sorted by frequency):
{value_distribution}

Known midPoint enum values:
{mp_enum_values}

Produce a Groovy script that maps each application value to the correct midPoint enum string.
""".strip()

suggest_categorical_mapping_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ("system", suggest_categorical_mapping_system_prompt),
        ("human", suggest_categorical_mapping_human_prompt),
        ("human", "{format_instructions}"),
    ]
)
