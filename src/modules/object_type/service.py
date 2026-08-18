# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
from typing import Iterable, List, Optional

from langchain.schema.output_parser import OutputParserException
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.common.llm import get_default_llm, make_basic_chain
from src.utils import pretty_json

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from .prompts import parser, prompt
from .schema import (
    ObjectTypeSuggestion,
    RegenerateMode,
    SuggestObjectTypeRequest,
    SuggestObjectTypeResponse,
)

logger = logging.getLogger(__name__)

"""
Service module for suggesting object types (kind, intent and delineation rules) using an LLM chain.
"""


def _object_type_context_item(suggestion: ObjectTypeSuggestion) -> dict:
    """
    Keep only fields useful for prompting and omit empty values.
    """
    item = {
        "kind": suggestion.kind,
        "intent": suggestion.intent,
        "displayName": suggestion.displayName,
        "description": suggestion.description,
        "filter": suggestion.filter,
        "baseContextFilter": suggestion.baseContextFilter,
        "baseContextObjectClassName": suggestion.baseContextObjectClassName,
    }
    return {key: value for key, value in item.items() if value not in (None, [], "")}


def build_existing_object_types_context(req: SuggestObjectTypeRequest) -> str:
    """
    Build the explicit saved/confirmed/rejected object-type context used by regeneration prompts.
    Returns a short plain-text marker when no context was supplied so the prompt remains deterministic.
    """
    saved = [_object_type_context_item(item) for item in (req.savedObjectTypes or [])]
    confirmed = [_object_type_context_item(item) for item in (req.confirmedSuggestions or [])]
    rejected = [_object_type_context_item(item) for item in (req.rejectedSuggestions or [])]

    if not saved and not confirmed and not rejected:
        return "No existing object type context was provided."

    payload = {
        "savedObjectTypes": saved,
        "confirmedSuggestions": confirmed,
        "rejectedSuggestions": rejected,
    }
    return "```json\n" + pretty_json(payload) + "\n```"


def build_feedback_messages(validation_errors) -> List[BaseMessage]:
    """
    Build a HumanMessage with a JSON code block from backend validation errors.
    Returns an empty list if there are no errors.
    """
    if not validation_errors:
        return []

    items = []
    for e in validation_errors or []:
        obj = getattr(e, "objectType", None)
        items.append(
            {
                "objectType": {
                    "kind": getattr(obj, "kind", None),
                    "intent": getattr(obj, "intent", None),
                    "displayName": getattr(obj, "displayName", None),
                    "filter": getattr(obj, "filter", None),
                    "baseContextFilter": getattr(obj, "baseContextFilter", None),
                },
                "filterErrors": list(getattr(e, "filterErrors", []) or []),
            }
        )

    payload = {
        "structured_validation_feedback": {
            "description": (
                "Backend returned previously suggested object types that must be corrected. "
                "ALL of them must be considered so that final rules stay mutually exclusive."
            ),
            "items": items,
        }
    }

    return [HumanMessage(content="\n```json\n" + pretty_json(payload) + "\n```")]


def build_regeneration_messages(
    regenerate_mode: RegenerateMode,
    previous_delineations: Optional[List[ObjectTypeSuggestion]],
) -> List[BaseMessage]:
    """
    Build a pair of chat messages describing why the user is regenerating and what was
    previously suggested: an AIMessage with the previous delineation JSON (simulating the
    prior model response) and a HumanMessage with the correction instruction.
    Returns an empty list if there are no previous delineations.
    """
    if not previous_delineations:
        return []

    items = []
    for d in previous_delineations:
        entry: dict = {"kind": d.kind, "intent": d.intent}
        if d.filter:
            entry["filter"] = d.filter
        if d.baseContextFilter:
            entry["baseContextFilter"] = d.baseContextFilter
        items.append(entry)
    prev_json = "```json\n" + pretty_json({"previousDelineation": items}) + "\n```"

    if regenerate_mode == RegenerateMode.NEW_DATA_SPLIT:
        return [
            AIMessage(content=prev_json),
            HumanMessage(
                content=(
                    "\n## Regeneration Request: New Data Split\n"
                    "The current partitioning is incorrect — the suggested delineation rules do not correctly split the data.\n"
                    "Generate a **completely different** set of delineation rules using a different partitioning strategy. "
                    "Do NOT replicate the same split logic as the previous suggestions above."
                )
            ),
        ]

    if regenerate_mode == RegenerateMode.NEW_FILTER:
        return [
            AIMessage(content=prev_json),
            HumanMessage(
                content=(
                    "\n## MANDATORY FILTER REPLACEMENT\n"
                    "The `(kind, intent)` labels above are correct, but every filter expression must be replaced.\n\n"
                    "**Rules you MUST follow:**\n"
                    "1. Keep exactly the same `kind` and `intent` values as shown above.\n"
                    "2. Treat all `filter` and `baseContextFilter` values above as **invalid** — do not copy either of them.\n"
                    "   This includes both MQL filter expressions and any base context (DN) filters.\n"
                    "3. Derive completely new MQL filter expressions by re-analysing the statistics from scratch.\n"
                    "4. If no better filter can be found for a rule, use `filter: null` rather than repeating the old one."
                )
            ),
        ]

    return []


async def suggest_delineation(req: SuggestObjectTypeRequest) -> SuggestObjectTypeResponse:
    """
    Suggest object-type delineations for the supplied statistics.

    :param req: SuggestObjectTypeRequest containing schema and statistical data.
    :returns: SuggestObjectTypeResponse containing object-type suggestions.
    """
    # 1) Build prompt payload and JSON
    stats_json = pretty_json(build_object_type_prompt_data(req))
    existing_object_types_context = build_existing_object_types_context(req)

    # 2) Build feedback messages (or empty list)
    feedback_messages: List[BaseMessage] = []
    if req.validationErrorFeedback:
        feedback_messages = build_feedback_messages(req.validationErrorFeedback)

    # 3) Build regeneration messages (or empty list)
    regen_messages: List[BaseMessage] = []
    if req.regenerateMode is not None:
        regen_messages = build_regeneration_messages(req.regenerateMode, req.previousDelineation)

    # 4) Invoke LLM chain
    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)

    try:
        delineation = await chain.ainvoke(
            {
                "stats_json": stats_json,
                "existing_object_types_context": existing_object_types_context,
                "regen_messages": regen_messages,
                "feedback_messages": feedback_messages,
            },
            config={"callbacks": [langfuse_handler]},
        )
    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc

    # 4) Build response
    suggestions = [
        ObjectTypeSuggestion(
            kind=rule.kind,
            intent=rule.intent,
            displayName=rule.displayName,
            description=rule.description,
            filter=_clean(getattr(rule, "filter", None)),
            baseContextFilter=getattr(rule, "baseContextFilter", None),
        )
        for rule in delineation.object_class.rules
    ]

    return SuggestObjectTypeResponse(objectType=suggestions)


def _clean(xs: Optional[Iterable[str]]) -> Optional[List[str]]:
    """
    Normalize string or list inputs into a clean list[str], or None if empty.
    Deduplicates while preserving order.
    """
    if not xs:
        return None
    if isinstance(xs, str):
        xs = [xs]
    cleaned = [s.strip() for s in xs if isinstance(s, str) and s.strip()]
    return list(dict.fromkeys(cleaned)) or None


def build_object_type_prompt_data(req: SuggestObjectTypeRequest) -> dict:
    """
    Transform the MidPoint statistics in *req* to the JSON payload that the
    LLM prompt expects.
    """
    stats = req.statistics
    size = stats.size

    schema = {
        "attributes": [
            {
                "name": attr.name,
                "type": attr.type,
            }
            for attr in req.applicationSchema.attribute
        ],
    }

    statistics = []
    for attr in stats.attribute:
        missing_ratio = (attr.missingValueCount / size) if size != 0 else 0.0
        unique_ratio = (attr.uniqueValueCount / size) if size != 0 else 0.0
        has_empty_values = not attr.valueCount and not attr.valuePatternCount
        if missing_ratio < 1.0 and not (
            unique_ratio == 1.0 and has_empty_values
        ):  # Skip attributes that are completely missing or have uniqueRatio 1.0 with empty values and patterns
            stat = {
                "column": attr.ref,
                "uniqueCount": attr.uniqueValueCount,
                "uniqueRatio": (attr.uniqueValueCount / size) if size != 0 else 0.0,
                "missingCount": attr.missingValueCount,
                "missingRatio": missing_ratio,
                "topN": len(attr.valueCount) if attr.valueCount else 0,
                "values": [{"value": vc.value, "count": vc.count} for vc in attr.valueCount] if attr.valueCount else [],
                "patterns": [
                    {"value": vpc.value, "type": vpc.type, "count": vpc.count} for vpc in attr.valuePatternCount
                ]
                if attr.valuePatternCount
                else [],
            }
            statistics.append(stat)

    # Crosstabs for attribute tuples
    crosstabs = [
        {
            "ref": t.ref,
            "counts": [{"value": tv.value, "count": tv.count} for tv in (t.tupleCount or [])],
        }
        for t in (stats.attributeTuple or [])
    ]

    return {
        "objectClass": req.applicationSchema.name,
        "schema": schema,
        "count": stats.size,
        "statistics": statistics,
        "crosstabs": crosstabs,
    }
