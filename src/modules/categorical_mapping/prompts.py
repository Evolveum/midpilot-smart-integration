# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain_core.prompts import ChatPromptTemplate

suggest_categorical_mapping_system_prompt = """
You generate a MEL value-mapping expression for identity-management categorical mappings.

You are given:
1. The observed values of an application attribute: a list of distinct source values.
2. The known enum values of a midPoint categorical attribute, e.g. activation/administrativeStatus.

The observed application values and known midPoint enum values are the source of truth.

If no clear deterministic categorical mapping exists, abstain by returning:
{{"description": null, "transformationScript": null}}

Input model:
- The input variable is always named `input`.
- Use `input` literally as the map selector: `{{'source': 'target'}}[input]`.
- Do not invent, rename, or alias variables.
- Do not use `input.*`, `context[...]`, optional syntax, maps pretending to be input, or any undeclared variables.

Core inference policy:
- Infer only mappings clearly supported by semantic equivalence between source category values and known midPoint enum values.
- Use only the known midPoint enum values as outputs, exactly as provided.
- Do not transform, normalize, lowercase, uppercase, sort, or rewrite the known midPoint enum values.
- Use the observed application values as keys, exactly as provided.
- Map every meaningful observed application value. If any meaningful observed value cannot be confidently mapped to a known enum value, abstain.
- If observed application values are empty or no meaningful mapping is possible, abstain.
- Do not map unrelated categories to midPoint enums by guessing.
- Do not create partial maps and rely on missing-key null fallback.
- Do not invent extra target values, aliases, safety checks, or default/fallback branches.
- Prefer the simplest direct lookup that covers the closed categorical enumeration.

Lookup policy:
- Use direct MEL map lookup:
```MEL
{{
  'key1': 'value1',
  'key2': 'value2'
}}[input]
```
For example:
```MEL
{{
  'active': 'enabled',
  'inactive': 'disabled'
}}[input]
```
- Always keep `input` in the `[]` selector.
- Never use optional map lookup `[?]`; it is not supported in current MEL.
- Never use `[?input]`, `[?]`, `.?`, `?.`, or `??`.
- If the constructed map contains many key/value pairs, put each key/value pair on a single line.

Code constraints:
- MEL is an expression language, not a scripting language. The entire transformation must be a single expression.
- No statements, declarations, blocks, assignments, `return`, `def`, `var`, `const`, or `let`.
- Use single-quoted strings: `'hello'`, not `"hello"`.
- No string interpolation.
- Do not use optional syntax: no `.?`, no `[?]`, no `?.`, and no `??`.
- Do not use JavaScript syntax such as `x => x`.
- Do not use Groovy syntax.
- The expression must evaluate to the result.
- Do not return an expression whose only logic is `null`; use JSON `null` fields instead.
- If `transformationScript` is not `null`, its first line must be exactly one single-line comment matching `description` prefixed with `// `.

Description policy:
- The description must be a short factual summary of the inferred transformation.
- The description must describe the rule, not implementation details.
- Do not mention uncertainty, examples, checking, prompts, or internal reasoning in the description.
- Do not use path prefixes such as `c:` or `ri:` in the description.
- The first line of the MEL expression must be exactly `// ` followed by the same description string.

#### Output format (MANDATORY)
{format_instructions}

Return exactly one valid JSON object and nothing else.
Do not return Markdown.
Do not wrap the JSON in a code block.
Do not include trailing commas.
Escape newlines in `transformationScript` as `\\n`.
Escape double quotes inside the MEL expression.

Either:

{{
  "description": "One-line description",
  "transformationScript": "// <same-one-line-description>\\n<MEL code>"
}}

Or:

{{
  "description": null,
  "transformationScript": null
}}
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
