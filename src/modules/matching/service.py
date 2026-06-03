# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from langchain.schema.output_parser import OutputParserException

from src.common.errors import LLMResponseValidationException
from src.common.llm import get_default_llm, make_basic_chain
from src.modules.matching.prompts import parser, prompt
from src.modules.matching.schema import (
    MatchSchemaRequest,
    MatchSchemaResponse,
    SchemaAttributeMatch,
)
from src.utils import pretty_json

from ...common.langfuse import langfuse_handler

logger = logging.getLogger(__name__)


"""Service module for matching schemas between application and MidPoint. """


def build_match_schema_prompt_data(
    req: MatchSchemaRequest,
) -> dict[str, dict[str, dict[str, str]]]:
    """
    Builds a dictionary containing schemas derived from midPoint and resource
    attributes. This function processes the information in the `req` parameter
    to generate a nested dictionary for midPoint and resource schemas. Each
    schema includes attribute names as keys and their metadata (type and
    description) as values.

    :param req: Input request data containing midPoint and application schema
        attributes.
    :return: A dictionary containing 'MidPoint_schema' and 'Resource_schema',
        where each contains attribute metadata in the form of nested dictionaries.
    """
    mid_schema = {
        attr.name: {"type": attr.type, "description": attr.description or ""} for attr in req.midPointSchema.attribute
    }
    resource_schema = {
        attr.name: {"type": attr.type, "description": attr.description or ""}
        for attr in req.applicationSchema.attribute
    }
    return {"MidPoint_schema": mid_schema, "Resource_schema": resource_schema}


async def match_midpoint_schema(
    req: MatchSchemaRequest,
) -> MatchSchemaResponse:
    """
    Processes and matches attributes between MidPoint schema and Resource schema based
    on the given request, invoking a language model chain to generate predictions and then
    validating and organizing results.

    :param req: The request data containing MidPoint schema and application schema
                attributes to match against.
    :return: A response object containing the matched attributes between MidPoint
             and application schema.
    """
    # 1. Build and serialize prompt
    prompt_data = build_match_schema_prompt_data(req)
    mid_json = pretty_json(prompt_data["MidPoint_schema"])
    res_json = pretty_json(prompt_data["Resource_schema"])
    # 2. Invoke the chain
    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)
    try:
        parsed = await chain.ainvoke(
            {
                "MidPoint_schema": mid_json,
                "Resource_schema": res_json,
            },
            config={"callbacks": [langfuse_handler]},
        )
    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc

    # 3. Build validity sets
    valid_midpoints = {a.name for a in req.midPointSchema.attribute}
    valid_resources = {a.name for a in req.applicationSchema.attribute}

    # 4. Group under each midpoint
    grouped: dict[str, set[str]] = {}
    for pair in parsed.pairs:
        mid = pair.MidPoint
        if mid not in valid_midpoints:
            continue
        ress = pair.Resource if pair.Resource else []
        for r in ress:
            if r in valid_resources:
                grouped.setdefault(mid, set()).add(r)

    # 5. Flatten into attributeMatch entries
    matches: list[SchemaAttributeMatch] = []
    for mid, ress in grouped.items():
        for r in ress:
            matches.append(
                SchemaAttributeMatch(
                    midPointAttribute=mid,
                    applicationAttribute=r,
                )
            )

    return MatchSchemaResponse(attributeMatch=matches)
