# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain.output_parsers import RetryWithErrorOutputParser
from langchain.prompts import BasePromptTemplate
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel
from langchain_openai import ChatOpenAI

from ..config import config


def get_default_llm(temperature: float = 1.0) -> ChatOpenAI:
    """
    Create and return a ChatOpenAI LLM instance with default parameters.

    :param temperature: Sampling temperature for the LLM (controls randomness).
    :return: Configured ChatOpenAI instance.
    """
    return ChatOpenAI(
        openai_api_key=config.llm.openai_api_key,
        openai_api_base=config.llm.openai_api_base,
        model_name=config.llm.model_name,
        request_timeout=config.llm.request_timeout,
        temperature=temperature,
        reasoning_effort="high",
        extra_body=config.llm.extra_body,
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

    chain = RunnableParallel(completion=completion_chain, prompt_value=prompt) | RunnableLambda(parse_with_retry)

    return chain
