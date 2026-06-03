# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from datetime import datetime
from typing import Any

from .config import config


# ---- parsing / normalization utilities ----
def normalize_attr_name_for_mel(name: str) -> str:
    """
    Normalize a namespaced MidPoint attribute name into a valid MEL identifier.

    MidPoint attribute names often carry namespace prefixes (e.g. ``c:name``,
    ``c:extension/ext:personalNumber``, ``c:attributes/ri:username``) which are
    invalid as MEL variable names because ``:`` is not a legal identifier
    character. MidPoint resolves the same attributes without the prefix, so
    stripping it is safe.

    The rule: take the substring after the **last** ``:`` in the name. This
    correctly handles all known patterns:

    - ``c:name``                         → ``name``
    - ``c:givenName``                    → ``givenName``
    - ``c:extension/ext:personalNumber`` → ``personalNumber``
    - ``c:attributes/ri:username``       → ``username``
    - ``c:attributes/icfs:name``         → ``name``
    - ``givenName`` (no prefix)          → ``givenName`` (unchanged)
    - ``attributes/username`` (path)     → ``username``
    - ``extension/personalNumber`` (path)→ ``personalNumber``

    :param name: Raw attribute name as received from MidPoint.
    :return: A valid MEL identifier string.
    """
    if ":" in name:
        return name.split(":")[-1]
    elif "/" in name:
        return name.split("/")[-1]
    else:
        return name


def _quote_single_by_type(raw: str, type_str: str) -> str:
    """
    Transform a single raw string into an appropriate string representation according to the given xsd type.

    - If the type_str parameter tells that the intended type of the raw value is a string, it wraps it with additional
      (escaped) quotes (e.g. "hello" -> "\"hello\"").
    - In case of other intended types, the raw value is returned as it is.

    The function also validates the raw value according to the specified xsd type by trying to parse it to its Python
    counterpart.

    :param raw: The raw string representation of the value.
    :param type_str: The XSD type string (e.g., "xsd:int", "xsd:datetime").
    :return: The potentially quoted string.
    :raises ValueError: If the value is invalid for the given type, or the type is unsupported.
    """
    v = raw.strip()
    t = type_str.strip().lower()

    if t == "xsd:boolean":
        val = v.lower()
        if val == "true" or val == "false":
            return val
        raise ValueError(f"Expected 'true' or 'false' for boolean, got {raw!r}")

    if t == "xsd:string":
        return f'"{v}"'

    if t in ("xsd:int", "xsd:long"):
        try:
            int(v)  # Check if it's a valid integer.
            return v
        except ValueError:
            raise ValueError(f"Invalid integer {raw!r} for type {type_str}")

    if t in ("xsd:double", "xsd:float"):
        try:
            float(v)  # Check if it's a valid float
            return v
        except ValueError:
            raise ValueError(f"Invalid float {raw!r} for type {type_str}")

    if t == "xsd:datetime":
        try:
            datetime.fromisoformat(v)  # Check if it's a valid datetime in iso format
            return v
        except Exception as e:
            raise ValueError(f"Invalid datetime {raw!r}: {e}") from e

    raise ValueError(f"Unsupported XSD type: {type_str!r}")


def quote_by_type(raw: Any, type_str: str, multivalued: bool = False) -> Any:
    """
    Quote input (expected to be a list, possibly empty) based on the xsd type.

    - If the type_str parameter tells that the intended type of the processed value is a string, it wraps it with
      additional (escaped) quotes (e.g. "hello" -> "\"hello\"").
    - In case of other intended types, the raw value is returned as it is.

    Empty list normalizes to None (if not multivalued) or [] (if multivalued).

    If multivalued, but with only one element, unwrapped element is returned.

    :param raw: The incoming raw value; expected to be a list or None.
    :param type_str: The XSD type string (e.g., "xsd:string", "xsd:int").
    :param multivalued: Whether the target schema allows multiple values.
    :return: Parsed value: single scalar (if not multivalued or multivalued with single item), list (if multivalued),
    or None for empties.
    """
    if raw is None:
        return [] if multivalued else None

    if not isinstance(raw, list):
        raise TypeError(f"Expected list for value, got {type(raw).__name__}: {raw!r}")

    if len(raw) == 0:
        return [] if multivalued else None

    parsed_list: list[Any] = []
    for item in raw:
        if item is None:
            parsed_list.append(None)
        else:
            parsed_list.append(_quote_single_by_type(str(item), type_str))

    if multivalued:
        if len(parsed_list) == 1:
            return parsed_list[0]
        return parsed_list
    if len(parsed_list) == 1:
        return parsed_list[0]
    raise ValueError(
        f"Expected single non-multivalued value for type {type_str}, got list of length {len(parsed_list)}"
    )


def pretty_json(value: Any) -> str:
    """
    Serialize a Python object into a human-readable JSON string.

    Uses UTF-8-friendly output (ensure_ascii=False) and 2-space indentation.
    """

    return json.dumps(value, ensure_ascii=False, indent=2)


def get_version_info():
    """
    Returns version name including git commit if available.
    """
    git_commit = config.app.git_commit
    version = config.app.version
    commit_info = f" ({git_commit})" if git_commit else ""
    return f"{version}{commit_info}"
