# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from textwrap import dedent

import pytest
from langchain.schema.output_parser import OutputParserException

from src.common.output_parsers import CodeSnippetOutputParser

parser = CodeSnippetOutputParser()

snippet = "println('Hello World');"


@pytest.mark.parametrize(
    "raw",
    [
        f"{snippet}",
        f"\n\n{snippet}\n",
    ],
)
def test_snippet_without_fences(raw):
    assert parser.parse(raw) == snippet


@pytest.mark.parametrize(
    "raw",
    [
        dedent(f"""
        ```
        {snippet}
        ```
        """),
        dedent(f"""
        ```groovy
        {snippet}
        ```
        """),
        dedent(f"""
        Here is the script:

        ```groovy
        {snippet}
        ```
        """),
    ],
)
def test_snippet_with_fences(raw):
    assert parser.parse(raw) == snippet


def test_multiline_snippets():
    raw = dedent("""
    see code snippet below:

    ```groovy
    // dummy comment

    if (true == true) {
        println('hello world');
    }

    println("done");

    ```
    """)
    assert (
        parser.parse(raw)
        == dedent(
            """
    // dummy comment

    if (true == true) {
        println('hello world');
    }

    println("done");
    """
        ).strip()
    )


def test_invalid_snippets():
    raw = dedent(f"""
    Option 1:

    ```groovy
    {snippet}
    ```

    Option 2:

    ```groovy
    {snippet}
    ```
    """)
    with pytest.raises(OutputParserException):
        parser.parse(raw)
