# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
import re

from langchain.schema.output_parser import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser

from src.common.llm import get_default_llm, make_basic_chain

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from ...utils import normalize_attr_name_for_mel, quote_by_type
from .prompts import suggest_mapping_prompt
from .schema import BaseSchemaAttribute, SuggestMappingRequest, SuggestMappingResponse, ValueExample

logger = logging.getLogger(__name__)


def build_prompt_data(req: SuggestMappingRequest) -> str:
    """
    Build a newline-separated string of mapping literals to use as few-shot examples.

    Scope: single-attribute mappings only (exactly one application attribute and one midPoint attribute).

    Output format (per example):
      - Inbound (application → midPoint):
          left  = [input: <application value>]
          right = <midPoint attribute value>
          Example: [input: "John"] -> "JOHN"

      - Outbound (midPoint → application):
          left  = [<midPointAttributeName>: <midPoint value>]
          right = <application value>
          Example: [givenName: "JOHN"] -> "John"

    :param req: Suggestion request.
                Expected shape:
                  - `applicationAttribute`: list with exactly one `BaseSchemaAttribute` (source attribute in the application)
                  - `midPointAttribute`: list with exactly one `BaseSchemaAttribute` (target attribute in midPoint)
                  - `inbound`: `True` for inbound (application → midPoint), `False` for outbound (midPoint → application)
                  - `example`: list of `IOExample` with `application` and/or `midPoint` `ValueExample` entries
    :return: A string where each line is a mapping literal: "<left> -> <right>".

    Notes:
      - Multi-value attributes are handled according to `maxOccurs` (True if > 1 or -1).
      - Empty lists are serialized as `null`.
      - For single-valued attributes, a parsed list is unwrapped to its first element.
      - Values are parsed via `parse_value_by_type(...)`.
    """

    if len(req.applicationAttribute) != 1 or len(req.midPointAttribute) != 1:
        raise ValueError("Only single-attribute mappings are supported.")

    app_attr = req.applicationAttribute[0]
    mid_attr = req.midPointAttribute[0]
    inbound = req.inbound

    def is_multi(attr: BaseSchemaAttribute) -> bool:
        return attr.maxOccurs > 1 or attr.maxOccurs == -1

    app_multi = is_multi(app_attr)
    mid_multi = is_multi(mid_attr)

    # general side-processing function; returns the literal string to emit
    def extract_and_emit(raw_examples: list[ValueExample] | None, attr: BaseSchemaAttribute, multi: bool) -> str:
        # pull out the raw string values (or [] if missing/empty)
        raw = next((ve.value for ve in (raw_examples or []) if ve.name == attr.name), [])
        val = quote_by_type(raw, attr.type, multivalued=multi)

        # empty-list → null
        if isinstance(val, list) and not val:
            return "null"

        # if single-valued but got a list, unwrap
        if not multi and isinstance(val, list):
            val = val[0]

        if val is None:
            return "null"
        if isinstance(val, list):
            return "[" + ", ".join(str(v) for v in val) + "]"
        return str(val)

    lines = []
    for ex in req.example:
        app_val = extract_and_emit(ex.application, app_attr, app_multi)
        mid_val = extract_and_emit(ex.midPoint, mid_attr, mid_multi)

        if inbound:
            source_literal = f"[input: {app_val}]"
            target_literal = mid_val
        else:
            mid_attr_name = normalize_attr_name_for_mel(mid_attr.name)
            source_literal = f"[{mid_attr_name}: {mid_val}]"
            target_literal = app_val

        lines.append(f"{source_literal} -> {target_literal}")

    return "\n".join(lines)


def is_null_script(script):
    if script is None:
        return True
    normalized = re.sub(r"//.*", "", script)
    normalized = normalized.strip()
    return not normalized or normalized == "null" or normalized == "return null"


async def suggest_mapping_script(req: SuggestMappingRequest) -> SuggestMappingResponse:
    """
    Suggest a MEL transformation expression for mapping input→midpoint values.
    Returns a Pydantic SuggestMappingResponse parsed by PydanticOutputParser.
    """
    # Build examples
    data_samples: str = build_prompt_data(req)

    llm = get_default_llm()
    parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=SuggestMappingResponse)
    chain = make_basic_chain(suggest_mapping_prompt, llm, parser)

    # Compose optional correction context from errorLog and previousScript
    context_parts = []

    if getattr(req, "errorLog", None):
        error_text = str(req.errorLog).strip()
        if error_text:
            context_parts.append(
                "IMPORTANT: The previous attempt failed backend validation. "
                "Read the error log below and correct your output accordingly.\n\n"
                "```\n" + error_text + "\n```"
            )

    if getattr(req, "previousScript", None):
        prev_script_text = str(req.previousScript).strip()
        if prev_script_text:
            context_parts.append(
                "PREVIOUS MEL EXPRESSION (this produced the error above; analyze and fix or rewrite as needed):\n\n"
                "```mel\n" + prev_script_text + "\n```"
            )

    error_context = "\n\n".join(context_parts).strip()

    try:
        resp: SuggestMappingResponse = await chain.ainvoke(
            {
                "data_samples": data_samples,
                "error_context": error_context,
                "format_instructions": parser.get_format_instructions(),
            },
            config={"callbacks": [langfuse_handler]},
        )
        # WORKAROUND: llm is instructed to return null if not possible to generate script, but it oftens leaves comments or returns null
        # FIXME: fix llm to follow `null` instruction or formalize e.g. using output parser
        if is_null_script(resp.transformationScript):
            resp.description = None
            resp.transformationScript = None
        return resp

    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc
