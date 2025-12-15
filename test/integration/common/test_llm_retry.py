# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import pytest
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from src.common.langfuse import langfuse_handler
from src.common.llm import get_default_llm, make_basic_chain


class Joke(BaseModel):
    topic: str = Field(..., description="Topic of the joke")
    rating: int = Field(..., description="Your subjective rating of the joke form 1 to 5")
    content: str = Field(..., description="Actual content joke.")


parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=Joke)


template = """
You are going to tell a joke about the {topic}.
Along with the content respond with your subjectiver rating.

{format_instructions}

First time I ask, intentionally respond with yaml. Next time fix it.
""".strip()

prompt = PromptTemplate(
    template=template,
    input_variables=["topic"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)


@pytest.mark.asyncio
async def test_basic_chain_retry_mechanism():
    llm = get_default_llm()
    chain = make_basic_chain(prompt, llm, parser)
    result = await chain.ainvoke({"topic": "cats"}, config={"callbacks": [langfuse_handler]})
    assert isinstance(result.topic, str)
    assert isinstance(result.content, str)
    assert isinstance(result.rating, int)
