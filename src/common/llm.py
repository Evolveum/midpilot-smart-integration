# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import asyncio
import logging
import ssl
from typing import Any, Awaitable

import httpx
import openai
from langchain.output_parsers import RetryWithErrorOutputParser
from langchain.prompts import BasePromptTemplate
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda, RunnableParallel
from langchain_openai import ChatOpenAI

from ..config import config as app_config
from .errors import LLMTimeoutException, LLMUnauthorizedException

logger = logging.getLogger(__name__)


async def invoke_with_auth_guard(coroutine: Awaitable[Any]) -> Any:
    """
    Await *coroutine* and translate OpenAI 401 authentication errors into a
    sanitized LLMUnauthorizedException that does not expose the API key.
    """
    try:
        return await coroutine
    except openai.APIStatusError as exc:
        if exc.status_code == 401:
            raise LLMUnauthorizedException from exc
        raise


def get_default_llm(temperature: float = 1.0) -> ChatOpenAI:
    """
    Create and return a ChatOpenAI LLM instance with default parameters.

    :param temperature: Sampling temperature for the LLM (controls randomness).
    :return: Configured ChatOpenAI instance.
    """
    verify: ssl.SSLContext | bool = (
        ssl.create_default_context(cafile=app_config.llm.ca_cert_file) if app_config.llm.ca_cert_file else True
    )

    http_client = httpx.AsyncClient(verify=verify)

    return ChatOpenAI(
        openai_api_key=app_config.llm.openai_api_key,
        openai_api_base=app_config.llm.openai_api_base,
        model_name=app_config.llm.model_name,
        temperature=temperature,
        reasoning_effort=app_config.llm.reasoning_effort,
        extra_body=app_config.llm.extra_body,
        http_async_client=http_client,
    )


def make_basic_chain(prompt: BasePromptTemplate, llm: ChatOpenAI, parser: BaseOutputParser) -> Runnable:
    """
    Creates a basic processing chain that combines a prompt template, a language model, and an output parser.

    :param prompt: The template for generating prompts.
    :param llm: The language model used for generating completions.
    :param parser: The parser for processing the output.
    :return: A runnable chain that processes input through the prompt, language model, and parser.
    """

    async def parse_with_retry(param):
        return await retry_parser.aparse_with_prompt(param["completion"].content, param["prompt_value"])

    completion_chain = prompt | llm

    # retries once if it fails with an error message
    # ref: https://python.langchain.com/docs/how_to/output_parser_retry/
    retry_parser = RetryWithErrorOutputParser.from_llm(parser=parser, llm=llm)

    inner_chain = RunnableParallel(completion=completion_chain, prompt_value=prompt) | RunnableLambda(parse_with_retry)

    async def _instrumented(input_value: Any, config: RunnableConfig) -> Any:
        timeout = app_config.llm.request_timeout

        logger.debug("LLM chain started, timeout=%ss", timeout)

        try:
            # Enforce the timeout around the whole LLM chain. Cancelling the chain propagates
            # cancellation to the underlying HTTP request e.g. LiteLLM.
            async with asyncio.timeout(timeout):
                result = await invoke_with_auth_guard(inner_chain.ainvoke(input_value, config))

            logger.debug("LLM chain completed")
            return result

        except TimeoutError as exc:
            logger.warning(
                "LLM chain timed out after %s seconds",
                timeout,
            )
            raise LLMTimeoutException(timeout) from exc

        except asyncio.CancelledError:
            logger.warning("LLM chain cancelled")
            raise

        except Exception:
            logger.exception("LLM chain failed")
            raise

    return RunnableLambda(_instrumented)
