# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
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
# IAM Schema Matching Task

Map MidPoint attributes to semantically corresponding Resource attributes.
Multiple Resource matches for one MidPoint attribute are allowed.

## Goal
- Prefer including plausible matches rather than missing true matches.
- The most important objective is to avoid missing correlator matches.
- Extra matches are acceptable; missing true correlator links is worse.
- If uncertain, include the candidate when there is plausible semantic evidence.
- Exclude only clearly unrelated matches.
- In ambiguous cases, favor semantic coverage of the concept over strict lexical matching.

## Correlators (All Object Types)
Correlators are MidPoint attributes used to find and link an existing focus object for the same entity
across systems.

Correlator sets:
- User correlators: `c:name`, `c:emailAddress`, `c:personalNumber`
- Non-User correlators: `c:name`, `c:identifier`, `c:emailAddress`

### Semantic meaning (generalized)
- `c:name`:
  treat as the primary identity handle used to find/reconcile the same entity.
  Match username/login handle, principal-style sign-in name, canonical object/account name,
  directory naming identity, alias, service/role/group handle, or provider-specific lookup handle.
  If a stable key is operationally used as primary lookup identity, it is a plausible `c:name`
  candidate even if formatted like an identifier.
- `c:emailAddress`:
  treat as routable mailbox/contact identity when used for lookup/linking/notification/ownership.
  Match deliverable mailbox, primary/secondary contact mailbox, alias, recovery/contact mailbox,
  or shared mailbox-style address.
  Include sign-in identifiers only when schema/docs indicate email-shaped identity.
- `c:personalNumber` (User):
  treat as workforce/person-record identity key.
  Match HR/staff/personnel/worker number, employee record key, payroll-linked person identifier,
  or organizational person reference used to uniquely link a human record.
  Include generic IDs only when semantics tie them to person identity.
- `c:identifier` (Non-User):
  treat as stable object identity key for Role/Service/Org/Policy-like entities.
  Match immutable/stable object code, system key, reference identifier, entity handle,
  canonical object identity, or canonical directory key used for cross-system reference.

### Correlator matching rules
- Identity-surface rule:
  if docs indicate account/object lookup identity, principal identity, mailbox/contact identity,
  canonical naming identity, directory naming identity, or stable person/object key,
  treat it as correlator-plausible.
- Multi-candidate recall rule:
  if multiple fields have comparable semantic evidence, include all plausible correlator candidates.
  Correlator false negatives are costlier than extra correlator candidates.
- Anti-overfitting guardrails:
  prioritize semantic function over lexical token overlap;
  do not require canonical naming conventions;
  accept provider-specific or legacy identity surfaces when behavior matches correlator intent.

These are the attributes of the MidPoint schema together with their descriptions (in Python dictionary format):
```json
{MidPoint_schema}
```

These are the attributes of the Resource schema together with their descriptions (in Python dictionary format):
```json
{Resource_schema}
```

## Workflow (Follow in Order)

1) Normalize names for comparison only (keep original keys in output):
   - Ignore prefixes/namespaces (e.g., c:, ri:).
   - Compare MidPoint path and especially its last segment.
   - Compare Resource full path and also last segment.
   - Compare case-insensitively and ignore separators "_", "-", ".", ":".

2) Build candidates for each MidPoint attribute:
   Include a Resource attribute if at least one is true:
   - names look similar after normalization, OR
   - description/type indicates the same business meaning, OR
   - it is a common IAM/SCIM synonym.
   Keep borderline but plausible candidates; remove only clearly unrelated fields.
   If several candidates look plausible, include all of them.

3) Correlator priority (highest-cost error = false negative):
   - For correlators, strongly prefer recall even if precision decreases.
   - If there is any plausible identity/linking signal, include the candidate.
   - If multiple fields have comparable evidence, include all plausible candidates.
   - Treat correlator evidence broadly across operational identity surfaces:
     stable technical IDs, external references, canonical or display handles,
     directory-native identities, and reachable contact identities when used for lookup/linking.
   - Treat nested/composite representations as equivalent to flat representations
     when they encode the same underlying entity identity.

4) Semantic rules for hard cases:
   - Match by business meaning, not by surface naming similarity.
   - Treat organizational placement as one concept even when represented differently
     (hierarchy, affiliation, placement, division-style structures).
   - Treat location/address as one concept even when one schema uses composite values
     and the other uses decomposed components.
   - Treat identity linkage fields as one concept even when the representation differs
     (human-readable handle, technical principal, directory identity, system key).
   - Treat lifecycle/state as one concept across different naming styles;
     if status semantics are equivalent, include the match.
   - For location/address semantics, include plausible components and structured subfields.
   - For organizational semantics, include plausible affiliation/placement subfields.
   - For descriptive/person-name/title semantics, include semantically close textual/profile variants.
   - Others FN recovery rules (include when semantics are consistent):
     `locality` can map to structured address components and formatted address text.
     `organization` can map to department/division/business-unit style fields.
     `organizationalUnit` can map to department/unit/path-style organizational placement fields.
     `lifecycleState` can map to active/enabled/disabled/suspended/lockout-style status fields.
     `description` can map to admin/internal description variants.
     `fullName` can map to administrative/display naming variants.
     `title` can map to personal/honorific title variants.
     `jpegPhoto` can map to profile/photo/avatar image fields.
     `locale` can map to locale/language/preferred-language style fields when they express user language context.

5) Rank Resource candidates (strongest -> weaker evidence):
   Prefer this order when applicable:
   1. Exact/near name match after normalization
   2. Strong semantic description/type match
   3. Common IAM/SCIM synonym match
   4. Weak but correlator-plausible identity surface (for correlators)

6) Final validation before output:
   - Use only attributes present in the provided schemas.
   - No duplicates in Resource candidate lists.
   - No empty/null values.
   - Each MidPoint attribute appears at most once.
   - Resource candidates must be unique and ordered strongest-to-weaker evidence.
   - Prefer under-filtering over over-filtering (better extra plausible candidates than missed true links).
   - If no plausible match exists for a MidPoint attribute, omit that MidPoint attribute from output.
   - Before omitting a MidPoint attribute, perform one last semantic sweep for concept-level matches:
     lifecycle/state, identity/linkage, naming/profile, organization/affiliation, contact channels,
     and geographic/address representation.

## Output Constraints
- Return ONLY valid JSON matching format instructions (no markdown, no comments).
- Use ONLY attributes present in the provided schemas; do not invent keys.
- Do NOT output empty lists, empty strings, or nulls.
- Resource candidates must be unique and ordered strongest-to-weaker evidence.

---
{format_instructions}
---
""".strip()


prompt = PromptTemplate(
    template=template,
    input_variables=["MidPoint_schema", "Resource_schema"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
