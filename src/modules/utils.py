# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import re

TAG_RE_PATTERN = r"""
</?                        # Opening or closing tag
(?:[a-zA-Z][\w:_-]*)       # Tag name pattern
(?:[\s]*[\w:_-]+=\".+\")?  # Optional attributes
\s*\/?>                    # Closing tag (allows endings like <hr>, <hr/>, <hr />)
"""
TAG_RE = re.compile(TAG_RE_PATTERN, re.VERBOSE)


def clean_description(text: str) -> str:
    """
    Remove XML/HTML tags (only if they are valid tags) and normalize whitespace.
    Preserves expressions with < and > like x>2, a<b, a<=b, a>=b.

    :param text: Input string that may contain HTML/XML tags and irregular whitespace.
                 If falsy (e.g., empty string or None), an empty string is returned.
    :return: The cleaned string with tags removed and whitespace normalized to single spaces.
    """
    if not text:
        return ""
    without_tags = TAG_RE.sub("", text)
    return " ".join(without_tags.split())
