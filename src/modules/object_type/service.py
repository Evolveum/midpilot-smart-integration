# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
from typing import Iterable, List, Optional

from langchain.schema.output_parser import OutputParserException

from src.common.llm import get_default_llm, make_basic_chain
from src.utils import pretty_json

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from .prompts import parser, prompt
from .schema import (
    ObjectTypeSuggestion,
    SuggestObjectTypeRequest,
    SuggestObjectTypeResponse,
)

logger = logging.getLogger(__name__)

"""
Service module for suggesting object types (kind, intent and delineation rules) using an LLM chain.
"""


def build_feedback_context_json(validation_errors) -> str:
    """
    Build a clean JSON code block for the prompt from backend validation errors.
    If there are no errors, return empty string -> prompt will not contain this section.
    """
    if not validation_errors:
        return ""

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

    # tu vyrobíme už celý code block
    return "```json\n" + pretty_json(payload) + "\n```"


async def suggest_delineation(req: SuggestObjectTypeRequest) -> SuggestObjectTypeResponse:
    """
    Suggest object-type delineations for the supplied statistics.

    :param req: SuggestObjectTypeRequest containing schema and statistical data.
    :returns: SuggestObjectTypeResponse containing object-type suggestions.
    """
    # 1) Build prompt payload and JSON
    stats_json = pretty_json(build_object_type_prompt_data(req))

    # 2) Build feedback JSON (or empty string)
    feedback_context = ""
    if getattr(req, "validationErrorFeedback", None):
        try:
            feedback_context = build_feedback_context_json(req.validationErrorFeedback)
        except Exception:
            # be defensive; do not block the flow on feedback formatting
            feedback_context = ""

    # 3) Invoke LLM chain
    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)

    try:
        delineation = await chain.ainvoke(
            {
                "stats_json": stats_json,
                "feedback_context": feedback_context,
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
