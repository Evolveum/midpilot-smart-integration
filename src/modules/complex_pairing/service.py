# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
from typing import Any, Dict, List

from src.utils import pretty_json

from ...common.errors import LLMResponseValidationException
from ...common.langfuse import langfuse_handler
from ...common.llm import get_default_llm, make_basic_chain
from .prompts import parser as verdict_parser
from .prompts import prompt_all
from .schema import ComplexPairingResponse

logger = logging.getLogger(__name__)


"""
Service module for complex record pairing using an LLM.

This module provides functionality for performing coarse matching between
MidPoint and Application records using a language model to determine
potential matches based on attribute values and their semantic similarity.
"""


def _pairs_json(req: Any) -> List[Dict[str, Any]]:
    """
    Convert the request pairs into a list of dictionaries with plain record representations.

    :param req: The request object containing record pairs to be matched. Must expose
                ``pairs``, where each pair has ``midPoint`` and ``application`` lists
                of Pydantic models.
    :return: A JSON-serializable list of dicts, each with ``midPoint`` and ``application``
             arrays of simplified record dicts.
    """
    record_include = {
        "identifier": True,
        "content": {"__all__": {"attribute", "value"}},
    }

    return [
        {
            "midPoint": [r.model_dump(mode="json", include=record_include) for r in p.midPoint],
            "application": [r.model_dump(mode="json", include=record_include) for r in p.application],
        }
        for p in req.pairs
    ]


async def complex_pairing(req: Any) -> ComplexPairingResponse:
    """
    Perform complex pairing between MidPoint and Application records using an LLM.

    This function takes a request containing pairs of records, converts them to a JSON
    format suitable for the LLM, and processes them through a chain that includes
    the LLM and a response parser.

    :param req: The request object containing record pairs to be matched.
    :return: A ComplexPairingResponse containing the matching results.
    """
    pairs_json = pretty_json(_pairs_json(req))

    llm = get_default_llm()
    chain = make_basic_chain(prompt_all, llm, verdict_parser)
    try:
        verdict = await chain.ainvoke({"pairs_json": pairs_json}, config={"callbacks": [langfuse_handler]})
    except Exception as exc:
        logger.exception("LLM chain failed in coarse_bk_match: %s", exc)
        raise LLMResponseValidationException() from exc

    data = verdict.model_dump() if hasattr(verdict, "model_dump") else verdict
    return ComplexPairingResponse.model_validate(data)
