# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from langchain.schema.output_parser import OutputParserException
from langchain_core.output_parsers import BaseOutputParser


class CodeSnippetOutputParser(BaseOutputParser[str]):
    """
    Parses raw string that is expecting a code block.
    If it contains markdown code block fences, it removes it.
    """

    def parse(self, text: str) -> str:
        lines = text.split("\n")
        md_fence_count = len([line for line in lines if line.startswith("```")])

        has_md_fence = md_fence_count > 0
        if has_md_fence and md_fence_count != 2:
            raise OutputParserException(
                f"CodeSnippetOutputParser expected fence count 2, actual {md_fence_count}:\n{text}"
            )
        if has_md_fence:
            inside_block = False
            inside_lines = []
            for line in lines:
                if line.startswith("```"):
                    inside_block = not inside_block
                    continue
                if inside_block:
                    inside_lines.append(line)
            result = "\n".join(inside_lines)
        else:
            result = text

        return result.strip()

    @property
    def _type(self) -> str:
        return "code_snippet_output_parser"
