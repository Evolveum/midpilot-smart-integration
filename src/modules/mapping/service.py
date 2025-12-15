# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from langchain.schema.output_parser import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser

from src.common.llm import get_default_llm, make_basic_chain

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from ...utils import parse_value_by_type, to_groovy_literal
from .prompts import suggest_mapping_prompt
from .schema import BaseSchemaAttribute, SuggestMappingRequest, SuggestMappingResponse, ValueExample

logger = logging.getLogger(__name__)


def build_prompt_data(req: SuggestMappingRequest) -> str:
    """
    Build a newline-separated string of Groovy mapping literals to use as few-shot examples.

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
    :return: A string where each line is a Groovy mapping literal: "<left> -> <right>".

    Notes:
      - Multi-value attributes are handled according to `maxOccurs` (True if > 1 or -1).
      - Empty lists are serialized as `null`.
      - For single-valued attributes, a parsed list is unwrapped to its first element.
      - Values are parsed via `parse_value_by_type(...)` and serialized with `to_groovy_literal(...)`.
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

    # general side-processing function
    def extract_and_emit(raw_examples: list[ValueExample] | None, attr: BaseSchemaAttribute, multi: bool):
        # pull out the raw string values (or [] if missing/empty)
        raw = next((ve.value for ve in (raw_examples or []) if ve.name == attr.name), [])
        val = parse_value_by_type(raw, attr.type, multivalued=multi)

        # empty-list → null
        if isinstance(val, list) and not val:
            val = None

        # if single-valued but got a list, unwrap
        if not multi and isinstance(val, list):
            val = val[0]

        return val

    lines = []
    for ex in req.example:
        app_val = extract_and_emit(ex.application, app_attr, app_multi)
        mid_val = extract_and_emit(ex.midPoint, mid_attr, mid_multi)

        if inbound:
            source_literal = f"[input: {to_groovy_literal(app_val)}]"
            target_literal = to_groovy_literal(mid_val)
        else:
            source_literal = f"[{mid_attr.name}: {to_groovy_literal(mid_val)}]"
            target_literal = to_groovy_literal(app_val)

        lines.append(f"{source_literal} -> {target_literal}")

    return "\n".join(lines)


async def suggest_mapping_script(req: SuggestMappingRequest) -> SuggestMappingResponse:
    """
    Suggest a Groovy transformation script for mapping input→midpoint values.
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
                "PREVIOUS GROOVY SCRIPT (this produced the error above; analyze and fix or rewrite as needed):\n\n"
                "```groovy\n" + prev_script_text + "\n```"
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
        return resp

    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc
