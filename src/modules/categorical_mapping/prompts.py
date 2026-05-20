# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain_core.prompts import ChatPromptTemplate

suggest_categorical_mapping_system_prompt = """
You generate a MEL value-mapping expression for identity management.

You are given:
1. The OBSERVED VALUES of an application attribute — a list of distinct values.
2. The KNOWN ENUM VALUES of a midPoint categorical attribute (e.g. activation/administrativeStatus). **These are the final, exact values — use them as-is without any transformations or safety checks.**

Your task is to produce a MEL expression that maps each observed application value to the most semantically appropriate 
midPoint enum string value.

#### Rules

1. For each application value, determine the best matching midPoint enum value based on semantic similarity (e.g. "1"/"true"/"active"/"enabled" → "enabled"; "0"/"false"/"inactive"/"disabled" → "disabled"; "deleted"/"archived" → "archived").
2. If an application value cannot be confidently mapped to any midPoint enum value, omit it.
3. **If no meaningful mapping is possible** between the application values and midPoint enum values (e.g., the application values are completely unrelated to the midPoint enum semantics), return `null` for the `transformationScript` field.
4. Use MEL maps as described in "MEL mapping expressions" section bellow to create a switch-like expression.
5. The input variable is always named `input` and it should be used as a "selector" of a value from constructed map. 
   It should be used literally in the `[?]` right after the map declaration `{{}}`.
6. MEL supports multiline expressions. If the constructed map contains a lot of key/value pairs, put each of them on 
   a single line.
7. The expression must start with exactly one single-line MEL comment describing the transformation (e.g. `// Map status values to activation/administrativeStatus`). No other comments are allowed. Do not use path prefixes (e.g. c:, ri:) in description.

#### MEL mapping expressions

In MEL, the expression which maps keys to values (similarly as `switch/case` in other languages) can be constructed as follows:
```MEL
{{
  'key1': 'value1',
  'key2': 'value2'
}}[?input]
```
For example:
```MEL
{{
  'active': 'enabled',
  'inactive': 'disabled'
}}[?input]
```

- **Always** keep the `input` in the `[?]`, that means `[?input]`. It acts as a selector of a particular value from the map.
- Use the observed values (values of an application attribute) as a keys
- Use the known enum values (possible values of the categorical midPoint property) as a values.

#### Output format (MANDATORY)
{format_instructions}

Return **exactly one JSON object** with this shape (escape newlines as `\\n` inside the string):

{{
  "description": "One-line description",
  "transformationScript": "// <same-one-line-description>\\n<MEL code>"
}}

**If no mapping is possible**, return:

{{
  "description": "No meaningful mapping possible",
  "transformationScript": null
}}

**Do not** include Markdown/code fences, language tags, XML/HTML tags, extra keys, or surrounding text. The JSON must be syntactically valid.
""".strip()

suggest_categorical_mapping_human_prompt = """
Application attribute: {app_attr_name} ({app_attr_type})
MidPoint attribute: {mp_attr_name}

Observed application values:
{app_enum_values}

Known midPoint enum values:
{mp_enum_values}

Produce a MEL expression that maps each application value to the correct midPoint enum string.
""".strip()

suggest_categorical_mapping_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ("system", suggest_categorical_mapping_system_prompt),
        ("human", suggest_categorical_mapping_human_prompt),
    ]
)
