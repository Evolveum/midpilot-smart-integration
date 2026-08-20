# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from langchain.schema.output_parser import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from ...common.llm import get_default_llm, make_basic_chain
from ...utils import is_null_script
from .prompts import suggest_categorical_mapping_prompt
from .schema import SuggestCategoricalMappingRequest, SuggestCategoricalMappingResponse

logger = logging.getLogger(__name__)


def build_prompt_data(req: SuggestCategoricalMappingRequest) -> dict:
    """
    Build prompt variables for the categorical mapping prompt.
    """
    app_enum_values = [f"  {v!r}" for v in req.applicationAttributeValue]
    return {
        "app_attr_name": req.applicationAttribute.name,
        "app_attr_type": req.applicationAttribute.type,
        "mp_attr_name": req.midPointAttribute.name,
        "app_enum_values": "\n".join(app_enum_values) if app_enum_values else "  (none)",
        "mp_enum_values": ", ".join(f'"{v}"' for v in req.midPointCategoryValue),
    }


async def suggest_categorical_mapping_script(
    req: SuggestCategoricalMappingRequest,
) -> SuggestCategoricalMappingResponse:
    """
    Suggest a MEL value-mapping expression for a categorical attribute.
    Uses value distribution and known midPoint enum values instead of data pairs.
    """
    prompt_vars = build_prompt_data(req)

    llm = get_default_llm()
    parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=SuggestCategoricalMappingResponse)
    chain = make_basic_chain(suggest_categorical_mapping_prompt, llm, parser)

    try:
        resp: SuggestCategoricalMappingResponse = await chain.ainvoke(
            {**prompt_vars, "format_instructions": parser.get_format_instructions()},
            config={"callbacks": [langfuse_handler]},
        )
        if is_null_script(resp.transformationScript):
            resp.description = None
            resp.transformationScript = None
        return resp

    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc
