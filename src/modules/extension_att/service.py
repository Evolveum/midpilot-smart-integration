# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from langchain.schema.output_parser import OutputParserException

from src.common.errors import LLMResponseValidationException
from src.common.llm import get_default_llm, make_basic_chain
from src.utils import pretty_json

from ...common.langfuse import langfuse_handler
from .prompts import ExtensionAttributes, parser, prompt
from .schema import SuggestExtensionRequest, SuggestExtensionResponse

logger = logging.getLogger(__name__)

"""Service module for suggesting extension attributes from UNMAPPED Resource attributes."""


def _build_extension_prompt_data(req: SuggestExtensionRequest) -> dict[str, str]:
    """
    Build JSON strings for the prompt from UNMAPPED Resource (application) attributes.

    :param req: Request object holding the ``applicationSchema`` with UNMAPPED attributes.
    :return: Dict with keys ``Resource_schema`` and ``Attribute_stats``. The
             schema maps attribute names to their metadata (type, description). The stats map
             attribute names to basic stats (totalCount, nuniq, nmissing).
    """
    resource_schema = {
        attr.name: {"type": attr.type, "description": attr.description or ""}
        for attr in req.applicationSchema.attribute
    }
    if req.attributeStats:
        # Convert Pydantic models to plain dicts for JSON serialization
        stats_dict: dict[str, dict] = {
            name: {
                "totalCount": s.totalCount,
                "nuniq": s.nuniq,
                "nmissing": s.nmissing,
            }
            for name, s in req.attributeStats.items()
        }
        attr_stats_json = pretty_json(stats_dict)
    else:
        attr_stats_json = pretty_json({})

    return {
        "Resource_schema": pretty_json(resource_schema),
        "Attribute_stats": attr_stats_json,
    }


async def suggest_extension(req: SuggestExtensionRequest) -> SuggestExtensionResponse:
    """
    Suggest attribute names for MidPoint extension based on UNMAPPED Resource (application) attributes.

    Processing steps:
    - Invoke the LLM with the resource schema and basic attribute stats.
    - Parse the structured response.
    - Post-process: trim, validate against input attribute names, de-duplicate while preserving order.
    - Return the selected attribute names AS-IS in the original resource namespace, e.g.,
      ``c:attributes/ri:personalNumber``.

    :param req: Request containing the application schema with UNMAPPED attributes
                under ``applicationSchema.attribute``.
    :return: ``SuggestExtensionResponse`` with resource attribute names as returned by the LLM
             (after filtering/deduplication), e.g., ``c:attributes/ri:personalNumber``.
    """
    variables = _build_extension_prompt_data(req)

    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)

    try:
        parsed: ExtensionAttributes = await chain.ainvoke(variables, config={"callbacks": [langfuse_handler]})
    except OutputParserException as exc:
        logger.exception("Extension suggestions output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc

    # Post-validation: keep only names that actually exist in the input, dedupe, preserve order
    valid_names = {attr.name for attr in req.applicationSchema.attribute}
    selected_resource_attrs: list[str] = []
    for name in parsed.extensionAttributes:
        n = name.strip()
        if n and (n in valid_names) and (n not in selected_resource_attrs):
            selected_resource_attrs.append(n)

    return SuggestExtensionResponse(extensionAttributes=selected_resource_attrs)
