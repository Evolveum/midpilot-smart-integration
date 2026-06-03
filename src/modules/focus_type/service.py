# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging

from langchain.schema.output_parser import OutputParserException
from langchain_core.prompts import ChatPromptTemplate

from src.common.llm import get_default_llm, make_basic_chain
from src.utils import pretty_json

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from .prompts import parser, suggest_focus_type_human_prompt, suggest_focus_type_system_prompt
from .schema import SuggestFocusTypeRequest, SuggestFocusTypeResponse

logger = logging.getLogger(__name__)

"""
Service module for suggesting a focus type (UserType, RoleType, OrgType, ServiceType)
based on application schema and context.
"""

# Build the prompt template
prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [
        ("system", suggest_focus_type_system_prompt),
        ("human", suggest_focus_type_human_prompt),
    ]
)


def build_focus_type_prompt_data(req: SuggestFocusTypeRequest) -> dict:
    """
    Transform the request into JSON payload expected by the prompt.

    :param req: SuggestFocusTypeRequest
    :return: dict representing the payload
    """
    schema_attrs = [attr.name for attr in req.applicationSchema.attribute]

    return {
        "objectClass": req.applicationSchema.name,
        "kind": req.kind,
        "intent": req.intent,
        "attributes": schema_attrs,
        "delineation": req.baseContextFilter,
    }


async def suggest_focus_type(req: SuggestFocusTypeRequest) -> SuggestFocusTypeResponse:
    """
    Execute the focus type suggestion chain using an LLM and return the top result.

    :param req: The SuggestFocusTypeRequest payload with schema and filters.
    :return: SuggestFocusTypeResponse containing the first suggested FocusType.
    """
    payload = build_focus_type_prompt_data(req)
    payload_json = pretty_json(payload)

    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)

    try:
        response: SuggestFocusTypeResponse = await chain.ainvoke(
            {"payload_json": payload_json},
            config={"callbacks": [langfuse_handler]},
        )
    except OutputParserException as exc:
        logger.exception("Output parsing failed: %s", exc)
        raise LLMResponseValidationException() from exc
    except Exception as exc:
        logger.exception("LLM invocation failed: %s", exc)
        raise LLMResponseValidationException() from exc

    return response
