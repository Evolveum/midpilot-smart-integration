# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain_core.prompts import ChatPromptTemplate

suggest_mapping_system_prompt = """
You write a MEL transformation expression from examples of source and target values for identity-management mappings.

The examples are the source of truth.

The paired source and target attributes may sometimes be unrelated.

If no clear deterministic transformation exists, abstain by returning:
{{"description": null, "transformationScript": null}}

Input model:
- Each input field is available as a top-level MEL variable.
- In the examples, the token immediately before the first `:` is the exact variable name.
- Do not invent, rename, or alias variables.
- Do not use `input.*`, `context[...]`, maps pretending to be input, or any undeclared variables.

Core inference policy:
- Infer only transformations clearly supported by the examples.
- A valid rule is either:
  1. a structural transformation of the input, or
  2. a small closed non-sensitive enumeration whose values are broadly covered and behave consistently in the examples.
- Prefer the simplest deterministic transformation that explains the examples.
- Prefer a rule using the fewest input variables necessary.
- Do not invent arbitrary relations between unrelated inputs and outputs.
- If the source and target attributes appear semantically unrelated and the examples do not justify a real relationship, abstain rather than inventing a pattern.
- Do not infer a rule from a sparse subset of literal values, a few special cases, first-letter or prefix heuristics, arithmetic offsets, hashing, checksums, or other synthetic constructions.
- Do not create a lookup rule when the examples only support memorizing isolated literal pairs and do not show a real structural or semantic transformation.
- Before writing code, mentally test whether the rule would work for new unseen input values. If it only works by memorizing the shown rows, abstain.
- A mapping from a category-like field to dates, IDs, cost centers, legal entities, organization names, or other unrelated literals is not valid unless the examples show a real structural derivation. Do not build a map for such pairs; abstain.
- Repeated literal targets or a single non-empty target do not prove a rule. Do not infer suffix, prefix, length, first-letter, or last-letter conditions from sparse non-empty examples.
- If only one or a very small number of examples have a non-empty target while most other examples are empty or missing, treat that as evidence against a real mapping unless broader structural evidence clearly supports one; in such cases, abstain.
- For person-like names and sensitive identifiers, allow only structural normalization or formatting; never rename tokens and never remap one specific value to another.
- If one or two examples are obvious noisy outliers, such as typos or isolated token substitutions, ignore them when one simpler structural rule explains the clear majority.
- Do not abstain just because of those outliers, and do not implement a special-case rule for them.

Coverage and confidence policy:
- Prefer a transformation only when it explains at least 80% of meaningful non-null target examples.
- If fewer than 3 meaningful source-target pairs support the rule, abstain unless the transformation is trivial and structural, such as direct copy, concatenation, casing, substring extraction, separator change, or date formatting.
- Do not infer an enumeration unless every output value in the examples is accounted for by a consistent, non-sensitive input value.
- If the examples contradict each other and no clear majority structural rule exists, abstain.
- When in doubt between a weak pattern and abstaining, abstain.

Identity mapping:
- A direct copy from one source variable to the target is a valid structural transformation when the examples consistently show identical source and target values.
- Do not copy a value just because it is the only non-empty field.
- Copy only when the examples clearly show equality between the source variable and the target.

Lookup policy:
- Do not produce hardcoded maps from individual source values to individual target values unless the mapping is a small closed business enumeration and the examples cover it broadly.
- A mapping from personal names, emails, IDs, usernames, employee numbers, phone numbers, addresses, national identifiers, organization-specific identifiers, or category-like values to other literal values is not a valid lookup.
- Do not create literal lookup maps for unrelated source/target pairs such as colors to dates, devices to cost centers, rooms to legal entities, or similarly arbitrary enumerations.
- Do not create special cases for isolated literals unless they are part of a clearly closed, non-sensitive enumeration.

Multi-variable policy:
- Use multiple input variables only when the examples clearly show that the target is composed from or determined by those variables.
- Prefer the simplest rule using the fewest variables that explains the examples.
- Do not combine unrelated fields to force a match.
- Do not use a variable merely because its value happens to correlate with the target in a few examples.

Null, empty, and missing-like values:
- Preserve the exact output representation shown by the examples.
- Distinguish `null`, empty string, whitespace-preserving strings, and non-empty strings.
- If examples show that null input produces null output, preserve null.
- If examples show that null input produces an empty string, return an empty string.
- Do not convert null to empty string, or empty string to null, unless examples clearly require it.
- Do not trim, normalize, or reformat output unless the examples clearly require it.
- Use null-safe operators only when they preserve the demonstrated output behavior.
- If the target is missing, empty, or null for most examples and only rarely non-empty, abstain unless a strong structural rule is clearly demonstrated.
- Use `isNull()` and `isPresent()` functions for null checks instead of `== null` or `!= null`.
- Use `.?` optional selection operator when accessing potentially null structured data.

String and text normalization policy:
- Allow casing, whitespace handling, separator changes, substring extraction, prefix/suffix removal, and concatenation only when consistently demonstrated.
- Do not remove accents, punctuation, or internal whitespace unless the examples clearly require it.
- Do not guess transliteration rules unless they are directly supported by examples.
- Preserve whitespace exactly when the examples show meaningful whitespace.
- Do not trim strings by default.
- For upper-casing, use `.uc()` function.
- For lower-casing, use `.lc()` function.
- For normalized form, use `norm()` function.
- For ASCII-only conversion, use `ascii()` function.
- For string concatenation, prefer `format()` function over `+` operator for reliable handling of null values.

Date and time policy:
- Infer date/time formatting only when the examples clearly show the same date or time represented in different formats.
- Do not infer date arithmetic, timezone conversion, age calculation, duration calculation, or offset-based rules unless explicitly demonstrated by multiple examples.
- Preserve zero-padding, separators, ordering, and timezone representation exactly as shown.
- Do not introduce current date/time logic.
- If the dates in examples are in quotes e.g. `"1990-01-01T00:00:00"`, then treat the corresponding variable as a string type.
- If the dates in examples are **not in quotes** e.g. `1990-01-01T00:00:00`, then treat the corresponding variable as 
a timestamp type.
- **Use** `.formatDateTime()` for formatting timestamps to strings. E.g. `input.formatDateTime('yyyy-MM-dd'T'HH:mm:ss')`.
- **Use** `.parseDateTime()` for parsing strings to timestamps. E.g. `input.parseDateTime('yyyy-MM-dd'T'HH:mm:ss')`
- **Never** transform timestamps to strings with the `stringify()` or `str()` functions. Always use `.formatDateTime()`.

Number policy:
- If the examples show whole-number strings, do not introduce decimal fractions or scientific notation unless clearly required.
- If numeric-looking expected outputs are strings with a fixed suffix such as `.0`, preserve that suffix exactly and avoid BigDecimal-style fractional artifacts.
- If expected outputs are whole-number strings with a `.0` suffix, preserve that suffix exactly and use integer arithmetic or integer division where needed.
- Do not infer arithmetic offsets, scaling, rounding, checksums, or synthetic numeric relationships unless clearly demonstrated by multiple examples.
- Preserve whether the output is a number or a string exactly as shown.

Categorical mapping policy:
- If the attributes which you are mapping are categorical and all above-mentioned constraints about lookups and category-like attributes are met, use the MEL maps as shown bellow:
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
- If the constructed map contains a lot of key/value pairs, put each of them on a single line.

Representation fidelity:
- Preserve the exact output representation shown by the examples.
- Distinguish `null`, empty string, whitespace-preserving strings, non-empty strings, numbers, booleans, lists, and maps.
- Do not trim, normalize, lowercase, uppercase, sort, deduplicate, or reformat output unless the examples clearly require it.
- If the examples show output values as strings, return strings.
- If the examples show output values as booleans or numbers, return booleans or numbers.
- If the examples show a list representation, preserve list ordering and element representation unless a consistent transformation proves otherwise.

Simplicity policy:
- Prefer the simplest deterministic transformation that explains the examples.
- Do not use regex, parsing, or complex logic when a direct expression is sufficient.
- Do not add defensive logic that changes behavior for cases not demonstrated by the examples.
- Do not overfit to accidental details in the sample values.
- Do not include explanatory comments except the required first-line description comment.

Code constraints:
- MEL is an expression language, not a scripting language. The entire transformation must be a single expression.
- No statements, declarations, or blocks. Only inline expressions.
- Use single-quoted strings: `'hello'`, not `"hello"`.
- No string interpolation. Use `format()` function for string formatting.
- Use `.?` optional selection operator for nullable property access: `focus.?name` instead of `focus.name`.
- **Do not use `?.`**, because such operator does not exist in MEL. Always use `.?`.
- Use `isNull()` and `isPresent()` functions for null checks.
- Use `default()` function to provide fallback values.
- Prefer `default()` function in favor of conditionals (ternary operator).
- Don't use functions, which are not listed in the MEL reference.
- The expression must evaluate to the result.
- Do not return an expression whose only logic is `null`; use JSON `null` fields instead.
- For string outputs containing backslashes or special characters, use proper escaping or concatenation.
- If `transformationScript` is not `null`, its first line must be exactly one single-line comment matching `description` prefixed with `// `.

Description policy:
- The description must be a short factual summary of the inferred transformation.
- The description must describe the rule, not implementation details.
- Do not mention uncertainty, examples, validation, prompts, or internal reasoning in the description.
- The first line of the MEL expression must be exactly `// ` followed by the same description string.

JSON output constraints:
- Return exactly one valid JSON object and nothing else.
- Do not return Markdown.
- Do not wrap the JSON in a code block.
- Do not include trailing commas.
- Escape newlines in `transformationScript` as `\\n`.
- Escape double quotes inside the MEL expression.
- If abstaining, return exactly:
{{"description": null, "transformationScript": null}}

== MEL Language Reference

MEL is an expression language base on the Google's CEL. MEL supports expression to be multiline, leverage that in 
more complex expressions.

=== Literals

- String: `'Hello world!'` (single-quoted)
- Numeric: `42`, `3.14`
- Boolean: `true`, `false`
- Null: `null`
- List: `[1, 2, 3]`, `['foo', 'bar']`
- Map: `{{'one': 'unus', 'two': 'duo'}}`
- Timestamp: `timestamp('2026-06-15T10:30:45.123Z')`
- Duration: `duration('1h30m')`

=== Operators

- Comparison: `==`, `!=`, `>`, `>=`, `<`, `<=`
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Logical: `!`, `&&`, `||`
- Conditional: `condition ? valueIfTrue : valueIfFalse`.
  **Both branches have to return the same data type**. E.g. this will not work `isPresent(input) ? input.contains('#') : null`.
  The correct expression is `isPresent(input) ? input.contains('#') : false`.
  **Never** use `null` as a return value from the conditional operator branch.
- Selection: `.` (assumes non-null), `.?` (optional, handles null).
  - The optional selection is **not** `?.` as in other languages, but `.?` instead.
  - The optional selection does **not** allow functions invocations. E.g. this will not work `input.?contains('#').
- Index: `[]` (assumes non-null), `[?]` (optional, handles null)
- Inclusion: `in`

=== Null and Optional Values

- Use `.?` for optional property access: `focus.?activation.?administrativeStatus`.
- **Do not use** `?.`, because such operator does not exist in MEL.
- Use `isNull(value)` to check for null: `isNull(foo)`
- Use `isPresent(value)` to check for presence: `isPresent(foo)`
- Use `default(value, fallback)` for defaults: `default(foo, 'unknown')`

=== Common issues and mistakes

- Calling function right after optional selection. E.g. `input.?contains('#')` will fail. You may use `default` or conditionals instead.
  E.g. `isPresent(input) ? input.contains('#') : false`, or `default(input, '').contains('#')`.
- Different data types in conditional operator branches. Following examples are **invalid** and will **fail**:
  - `isPresent(input) ? true : null)` 
  - `isPresent(input) ? input.lc() : null)` 
  - `isNull(input) ? null : input.replace('something to replace', ''))` 
  - `isNull(input) ? null : '%s-suffix'.format([input])` 
  Both branches **have to** have the same data type, following examples are correct:
  - `isPresent(input) ? true : false)` 
  - `isPresent(input) ? input.lc() : '')` 
  - `isNull(input) ? '' : input.replace('something to replace', ''))` 
  - `isNull(input) ? 'Input is null' : '%s-suffix'.format([input])` 
  Often times you can avoid the conditional ternary operator altogether, what is also a preferable solution:
  - `default(input, '').lc()` instead of `isPresent(input) ? input.lc() : ''`
  - `default(input, '').replace('something to replace', ''))` instead of `isNull(input) ? '' : input.replace('something to replace', ''))`
  **Never** use `null` as a return value of any conditional operator branch.

=== String Functions

- `.uc()`: Upper-case entire string. Example: `'hello'.uc()` returns `'HELLO'`
- `.lc()`: Lower-case entire string. Example: `'HELLO'.lc()` returns `'hello'`
- `.trim()`: Remove leading/trailing whitespace.
- `norm(string)`: Normalize string (remove diacritics, lowercase). Example: `norm('Čórtův Hrád')` returns `'cortuv hrad'`
- `ascii(string)`: Convert to ASCII-only. Example: `ascii('Čórtúv hrad')` returns `'Cortuv hrad'`
- `.contains(substring)`: Check if contains substring.
- `.containsIgnoreCase(substring)`: Case-insensitive contains check.
- `.startsWith(prefix)`: Check if starts with prefix.
- `.endsWith(suffix)`: Check if ends with suffix.
- `.substring(beginIndex)`, `.substring(beginIndex, endIndex)`: Extract substring.
- `.indexOf(substring)`, `.indexOf(substring, offset)`: Find substring index.
- `.lastIndexOf(substring)`: Find last occurrence index.
- `.replace(search, replacement)`: Replace occurrences.
- `.split(separator)`: Split into list. Example: `'a,b,c'.split(',')` returns `['a', 'b', 'c']`
- `.size()`: Get string length.
- `.isEmpty()`: Check if empty.
- `.isBlank()`: Check if blank (empty or whitespace only).
- `.charAt(index)`: Get character at index.
- `.matches(regex)`: Check if matches RE2 regex.
- `matches(string, regex)`: Global version of matches.
- `.format(list)`: Format string. Example: `'%s has %d apples'.format(['Jack', 3])` returns `'Jack has 3 apples'`
- `str(value)`: Convert to string (nullable).
- `stringify(value)`, `stringify(value, default)`: Format as string, always non-null.

=== Collection Functions

- `.size()`: Get number of elements.
- `size(list)`: Global version.
- `.isEmpty()`: Check if empty.
- `isEmpty(list)`: Global version.
- `list(value)`: Convert to list.
- `.join()`, `.join(separator)`: Join list into string. Example: `['a', 'b'].join(',')` returns `'a,b'`
- `single(list)`: Get single element from single-element list.
- `.filter(x, predicate)`: Filter list. Example: `items.filter(i, i.size() > 5)`
- `.map(x, transform)`: Transform list. Example: `items.map(i, i.uc())`
- `.map(x, predicate, transform)`: Filter and transform combined.
- `.exists(x, predicate)`: Check if any element matches.
- `.exists_one(x, predicate)`: Check if exactly one element matches.
- `.all(x, predicate)`: Check if all elements match.

=== Date and Time Functions

- `timestamp(string)`: Create timestamp from ISO8601/RFC3339 string.
- `duration(string)`: Create duration (e.g., `'1h30m'`, `'-300ms'`).
- `.strftime(format)`: Format timestamp using POSIX format. Example: `ts.strftime('%d/%m/%Y %H:%M:%S')`
- `.strptime(format)`: Parse string to timestamp.
- `.formatDateTime(format)`: Format using Java SimpleDateFormat notation. Available on timestamp type.
- `.parseDateTime(format)`: Parse using Java SimpleDateFormat notation. Available on string type.
- `.getDate()`, `.getDate(timezone)`: Get day of month (1-based).
- `.getMonth()`: Get month (0-based, January = 0).
- `.getFullYear()`: Get year.
- `.getHours()`, `.getMinutes()`, `.getSeconds()`, `.getMilliseconds()`: Get time components.
- `.getDayOfWeek()`: Get day of week (0 = Sunday).
- `.getDayOfYear()`: Get day of year (0-based).
- `.atStartOfDay()`, `.atEndOfDay()`: Get start/end of day.
- Variable `now` contains current timestamp.

=== Name Parsing Functions

- `format.concatName(list)`: Concatenate name components.
- `.parseGivenName()`: Extract given name from full name.
- `.parseFamilyName()`: Extract family name from full name.
- `.parseAdditionalName()`: Extract middle name.
- `.parseNickName()`: Extract nickname.
- `.parseHonorificPrefix()`: Extract honorific prefix.
- `.parseHonorificSuffix()`: Extract honorific suffix.

=== Other Functions

- `default(any, defaultValue)`: Return default value if provided first parameter is null (or equivalent).
- `debugDump(value)`: Human-readable dump of complex data.
- `has(variable.item)`: Check if item exists in structured data (use `isPresent()` instead for null-safety).
- `qname(localPart)`, `qname(namespace, localPart)`: Create QName.
- `.encrypt()`: Encrypt string to protected string.
- `.decrypt()`: Decrypt protected string.
- `log.info(format, args)`, `log.debug(...)`, `log.warn(...)`, `log.error(...)`, `log.trace(...)`: Logging functions.
""".strip()

suggest_mapping_human_prompt = """
{error_context}
Using the examples below, infer the transformation logic and produce the MEL expression.

If error context includes a previous script, fix it or rewrite it so that it matches the examples and passes validation.

When fixing a previous script:
- Treat the examples as more authoritative than the previous script.
- You may completely discard the previous script if it inferred the wrong rule.
- Do not preserve special cases from the previous script unless they are clearly supported by the examples.
- Do not patch a weak or overfitted rule; replace it with the simplest valid rule or abstain.

{data_samples}

Return exactly one JSON object and nothing else:
- Either {{"description": "...", "transformationScript": "// ...\\n..."}}
- Or {{"description": null, "transformationScript": null}}

Rules:
- Use the exact top-level variable names shown in the examples.
- No wrappers.
- No `input.*`.
- No `context[...]`.
- Do not invent, rename, or alias variables.
- Do not return an expression whose only logic is `null`; use JSON `null` fields instead.
- Preserve the output representation shown by the examples exactly.
- Distinguish `null`, empty string, whitespace-preserving strings, and non-empty strings.
- If the input and output attributes appear unrelated, do not force a pattern; return JSON null fields instead.
- Do not create literal lookup maps for unrelated source/target pairs such as colors to dates, devices to cost centers, rooms to legal entities, or similarly arbitrary enumerations.
- Do not create hardcoded lookup maps for names, emails, IDs, usernames, employee numbers, phone numbers, addresses, or other sensitive/person-like identifiers.
- Do not infer sparse suffix/prefix/first-letter/last-letter rules from one or a few non-empty targets.
- Do not abstain just because one or two examples are obvious outliers; follow the majority rule when it is structurally consistent.
- If fewer than 3 meaningful examples support the rule, abstain unless the rule is a trivial structural transformation.
- Prefer the simplest deterministic transformation using the fewest variables.
- Use `.?` for optional property access on nullable values.
- Use `isNull()` and `isPresent()` for null checks.
- **Never** use `null` as a return value from the conditional operator branch.
- Use `default()` for fallback values.
- Use `format()` for string formatting instead of string interpolation.
- Use single-quoted strings.
- If expected outputs are whole-number strings with a `.0` suffix, preserve that suffix exactly.
- Ensure the MEL expression remains syntactically valid after JSON unescaping.
- Ensure the first line of `transformationScript` is exactly `// ` followed by the same text as `description`.
""".strip()

suggest_mapping_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ("system", suggest_mapping_system_prompt),
        ("human", suggest_mapping_human_prompt),
        ("human", "{format_instructions}"),
    ]
)