# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from langchain.schema.output_parser import OutputParserException

from src.common.errors import LLMResponseValidationException
from src.common.llm import get_default_llm, make_basic_chain
from src.modules.correlation.prompts import parser, prompt
from src.modules.correlation.schema import (
    SuggestExtensionCorrelatorsRequest,
    SuggestExtensionCorrelatorsResponse,
)
from src.utils import pretty_json

from ...common.langfuse import langfuse_handler

logger = logging.getLogger(__name__)


"""Service module for suggesting correlators from midPoint extension attributes."""


def _build_prompt_inputs(req: SuggestExtensionCorrelatorsRequest) -> dict:
    """
    Build prompt variables for the LLM chain in one place.

    :param req: Request carrying MidPoint schema context, extension attributes and their basic stats.
    :return: Dict with keys expected by the prompt template: `schema_name`, `schema_description`,
             `extension_attributes` (JSON string) and `attributeStats` (JSON string).
    """
    attrs = [
        {
            "name": a.name,
            "type": a.type,
            "description": a.description or "",
        }
        for a in req.extensionAttributes
    ]
    ext_json = pretty_json(attrs)

    # Serialize stats
    stats_payload = {k: v.model_dump() for k, v in req.attributeStats.items()}
    stats_json = pretty_json(stats_payload)

    return {
        "schema_name": req.schemaName,
        "schema_description": req.schemaDescription or "",
        "extension_attributes": ext_json,
        "attributeStats": stats_json,
    }


async def suggest_extension_correlators(
    req: SuggestExtensionCorrelatorsRequest,
) -> SuggestExtensionCorrelatorsResponse:
    """
    Suggest suitable correlator attributes from MidPoint extension attributes using LLM guidance.

    :param req: Request with MidPoint `schema_name`, optional `schema_description`,
                `extension_attributes` (list of attributes) and `attributeStats` (basic stats per attribute).
    :return: Response with `correlators` containing only attribute names selected for correlation.
    """
    # 1) Prepare serialized inputs for the prompt
    prompt_vars = _build_prompt_inputs(req)

    # 2) Build the chain
    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)

    # 3) Invoke the chain and parse
    try:
        parsed = await chain.ainvoke(prompt_vars, config={"callbacks": [langfuse_handler]})
    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc

    # 4) Return as response model
    return SuggestExtensionCorrelatorsResponse(correlators=parsed.correlators)
