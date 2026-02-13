# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field


class Rule(BaseModel):
    """One delineation rule for an object class."""

    kind: str = Field(..., description="MidPoint kind attribute")
    intent: str = Field(..., description="MidPoint intent attribute")
    displayName: str = Field(..., description="A user-friendly name representing the combination of kind and intent")
    description: str = Field(..., description="A detailed explanation describing the chosen delineation")

    # MQL expressions to combine with logical AND
    filter: Optional[List[str]] = Field(
        None,
        description='List of MQL expressions for this rule; combine items with logical AND, e.g. ["a = 1", "b startsWith \\"X\\""].',
    )

    # Base-context scope for the rule
    baseContextFilter: Optional[str] = Field(
        None,
        description='MQL expression scoping the base context (e.g. "c:attributes/ri:dn = "ou=projects,dc=example,dc=com"").',
    )

    def model_post_init(self, __context):
        # Ensure DN values in baseContextFilter are properly quoted
        if self.baseContextFilter and "=" in self.baseContextFilter:
            parts = self.baseContextFilter.split("=", 1)
            if len(parts) == 2:
                left, right = parts
                right = right.strip()
                # If the right side is not already quoted, add quotes
                if not (right.startswith('"') and right.endswith('"')):
                    self.baseContextFilter = f'{left}= "{right}"'

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Convert string filters to single-item lists
        if isinstance(obj, dict):
            if "filter" in obj and isinstance(obj["filter"], str):
                obj["filter"] = [obj["filter"]]
        return super().model_validate(obj, **kwargs)


class ObjectClass(BaseModel):
    """One object class from the dataset with its delineation rules."""

    name: str = Field(..., description="Object class name")
    rules: List[Rule] = Field(..., description="Mutually-exclusive delineation rules for this object class")


class Delineation(BaseModel):
    """Single object class with its set of delineation rules."""

    object_class: ObjectClass = Field(..., description="Object class with its delineation rules")


parser: PydanticOutputParser[Delineation] = PydanticOutputParser(pydantic_object=Delineation)

template = """
You are given schema and statistical characteristics of the dataset representing a single object class.
Your task is to find patterns in the data that are subject to so-called delineation - the data is devided into smaller subsets that logically (and according the rules below) belongs together.
Next you will generate filters to query each subset in midPoint Query Language (MQL).
Each filter encodes a single delineation rule for that object class, partitioning its dataset accordingly.
The response contains data related to given object class with **multiple** mutually-exclusive rules.
Ensure every rule is valid MQL using the midPoint data model and follows all quoting and syntax conventions.

## ⚠️ IMPORTANT (IGA CONTEXT)
- These delineation filters are used in **Identity Governance & Administration (IGA)**.
- Filters MUST rely only on **IGA-relevant resource attributes** (e.g. employeeNumber, uid, login, dn, groupType, entitlement identifiers).
- **Stability requirement:**
  - The delineation rule identifies a pattern/category in the data that is expected to be stable and it is unlikely that data changes category over time.
  - Therefore use only attributes it's values that are expected to be stable and constant over time (e.g., identifiers, technical types, DN/OU scope, technical prefixes/suffixes, ...).
  - Avoid using attributes and it's values that are likely to change (e.g., manager/supervisor references, volatile org metadata, ...).
- DO NOT use personal data such as names, surnames, addresses, phone numbers, emails, locations, or descriptions as filter criteria.
- Any rule based on such personal information is INVALID.
- It is valid that sometimes there is only **one rule** for the whole object class:
  - In that case, the rule may have no `filter` or `baseContextFilter`.
  - Such a rule still needs unique `(kind, intent)` labels.

## Special Guidance for Rule Construction
- If the same attribute shows both **prefix** and **suffix** patterns, choose **only one** type of patterning (whichever provides clearer partitioning). Do not emit both for the same attribute.
- If an attribute is **present for some objects but missing for others**, this difference itself is an important delineation criterion. You may create rules based on **existence** checks using `path exists` / `path not exists` (e.g. `employeeNumber exists`).
- Rules may be composite: e.g. one branch checks presence of an identifier, while another branch uses prefixes for specific values, and a final branch covers the remainder.
  Composite rules may combine multiple attributes **only if a dependency between them is explicitly shown in the `crosstabs` section**.
  If no such crosstab evidence exists, treat the attributes separately in different rules.
- Always ensure rules are **mutually exclusive** and collectively exhaustive (include a catch-all if necessary).
- Only combine attributes into one rule if there is statistical evidence of dependency between them (e.g. provided in `crosstabs`).
- If no crosstab shows dependency, treat attributes independently and do not artificially combine them in one filter.
- The number of delineation rules should be reasonable. In practice, one object class is usually partitioned into **fewer than 10 groups**.
  Avoid over-fragmentation into many small rules; prefer broader, meaningful partitions.

## Simplicity-First & Complexity Guard (add-on)
Prefer simple, robust delineations. If a rule would become too complex, fall back to a single-rule delineation (no `filter`, no `baseContextFilter`).

Trigger the fallback when ANY of these holds:
- A rule needs more than 5 disjuncts (more than three `or` clauses) on the same attribute.
- A rule needs more than 4 anti-conditions (`not (...)`) to exclude overlaps.
- You would have to enumerate many literal prefixes/suffixes on one attribute to get coverage.
- DN scoping would require multiple disjoint bases (i.e., there is no single clean DN base).

Fallback behavior:
- Emit exactly one rule with `filter = null` and `baseContextFilter = null`.
- Use a generic, semantically appropriate label (e.g., `entitlement/default` for groups, `account/default` for accounts).
- In the rule description, state that no stable, simple IGA-relevant partition exists for this object class.


## Conflict Resolution (GENERAL): Hierarchical Partitioning with Anti-Conditions
When signals overlap (e.g., administrative/service indicators vs. presence of authoritative identifiers), enforce **hierarchical rules**:
1) **Order signals by priority** from strongest to weakest. Typical IGA order:
   - Administrative/service indicators in technical IDs (prefix/suffix patterns in uid/login/accountId).
   - Authoritative identifiers and their presence/absence (**`path exists` / `path not exists`**, e.g., `employeeNumber exists`).
   - Organizational context via DN (`DNsuffix` → use `baseContextFilter`).
   - Other stable technical attributes (account type, groupType, department codes).
   - Catch-all.
2) For **each lower-priority rule**, add **anti-conditions** excluding **all higher-priority** signals using `not (...)` so the rules are **mutually exclusive**.
3) Add a final **catch-all** rule that excludes all higher-priority signals.
4) Do **not** treat anti-conditions as evidence of dependency; they are used purely to eliminate overlap. Only combine attributes in a single rule if `crosstabs` explicitly shows dependency.

### Skeleton (pseudocode → MQL)
Assume prioritized predicates `PRIMARY_i` (MQL expressions for each priority):
- Rule 1 (highest): `filter: ["PRIMARY_1"]`
- Rule 2: `filter: ["PRIMARY_2", "not (PRIMARY_1)"]`
- Rule 3: `filter: ["PRIMARY_3", "not (PRIMARY_1)", "not (PRIMARY_2)"]`
- ...
- Catch-all: `filter: ["not (PRIMARY_1)", "not (PRIMARY_2)", "not (PRIMARY_3)"]`
*(If using DN branches, place the DN base in `baseContextFilter` and other conditions in `filter`.)*

## MQL Syntax Summary
- Attributes are never PolyString.
- Comparison operators: =, !=, <, <=, >, >=
- String filters:
  path startsWith "…",
  path endsWith "…",
  path contains "…"
- Logical operators: and, or, not (use parentheses to group)
- **Existence checks**: `path exists` / `path not exists` (attribute or container presence)
- Matching rules (for string):
  By default, strings are case-sensitive. For case-insensitive search use matching rule stringIgnoreCase:
  path startsWith[stringIgnoreCase] "…", endsWith[stringIgnoreCase] "…", contains[stringIgnoreCase] "…"

## Quoting Rules
- String comparisons: wrap values in double quotes exactly once (e.g. `objectClass = "group"`).
- Numeric comparisons: use bare numbers without quotes (e.g. `groupType = -2147483646.0`).
- Do not introduce extra quotes around numbers or strings.

## General Constraints
- Do not use the `kind` or `intent` attributes in the filter expression itself.
- Do not use any timestamp or date attributes in the filter expression.
- NEVER use `description` in the filter expression.
- You are predicting `(kind, intent)` as labels for each rule based on other attributes, but those labels must **not** appear in the MQL.
- When referencing an attribute in your filter, always use the name as-is (e.g. `fullname`).
- Each `(kind, intent)` pair must be **unique**. Do not define more than one rule for the same combination of kind and intent.
- Rules must not include any personal information.

## Value Pattern Types
1. **prefix** → use `startsWith`
2. **suffix** → use `endsWith`
3. **firstToken** → typically `startsWith`
4. **lastToken** → typically `endsWith`
5. **DNsuffix** → custom value pattern for LDAP `dn`, matching the suffix of the DN starting from the first `ou` RDN.

### Special Handling for `DNsuffix`
- When a rule leverages `DNsuffix` on `dn`, specify the DN base(s) using `baseContextFilter`.
- You may also include additional attribute-level expressions in `filter`.
- The effective rule condition is:
  **AND of all items in `baseContextFilter`** AND **AND of all items in `filter`** (if present).

## Schema Constraints
- `filter` is a list of MQL expressions; the effective rule filter is the logical AND of all list items.
- baseContextFilter MUST be a single string and MUST start with `dn =`. Do not use any other MQL in baseContextFilter.
- Both fields may be present simultaneously in a single rule; evaluate the final rule as:
  `AND(baseContextFilter) AND AND(filter)`.
- All rules for an object class must be mutually exclusive (their evaluated conditions must not overlap).

## Rule Construction Steps
1. Exclude any rules with `coverage = "else"` coming from upstream inputs (you'll add your own catch-all if needed).
2. Ensure all rules are per object class and mutually exclusive (no overlaps).
3. If coverage does not reach 100%, add a catch-all rule for the remaining subset (design it so it does not overlap with existing rules).

### Kinds (predicted labels)
- `account`     : user identities (human, admin, service, daemon)
- `entitlement` : groups, roles, permissions, org-unit memberships
- `generic`     : all other resources (LDAP OUs, servers, applications, licenses, cards)

### Intents (predicted labels) examples
`default`, `admin`, `testing`, `employee`, `service`, `customer`, ...

### Using `stats_json`
- The input `stats_json` maps attributes to observed values and counts.
- You may partition by a single attribute (emit one filter rule per distinct value),
  by DN bases (emit one baseContextFilter rule per base),
  or a mix. When mixing, you may use both `baseContextFilter` (to scope to a DN subtree) and `filter` (to refine further) in the same rule.
- If branches don’t sum to full coverage, include a final catch-all rule.

--------------------
## JSON statistics for this object class:
```json
{stats_json}
```
--------------------


{feedback_context}


#### Format instruction:
--------------------
{format_instructions}
""".strip()

prompt = PromptTemplate(
    template=template,
    input_variables=["stats_json", "feedback_context"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
