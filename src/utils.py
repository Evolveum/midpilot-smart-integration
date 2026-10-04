# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
import re
from datetime import datetime
from typing import Any

from src.common.errors import InvalidValueException

from .config import config

# ---- parsing / normalization utilities ----
_COMMON_NS_PREFIX_PATTERN = re.compile(r"(?<![\w:=])c:")


def strip_common_prefix(path: Any) -> Any:
    """
    Remove the redundant ``c:`` (common-3) namespace prefix from item path segments.

    MidPoint historically serializes item paths like ``c:attributes/ri:emptype`` or
    ``c:name``. Newer versions send plain ``attributes/ri:emptype`` / ``name`` —
    both forms are equivalent, so this makes the service accept legacy requests
    without exposing the ``c:`` prefix to the LLM.

    Only segment-leading ``c:`` is stripped (start of string or after ``/``), so
    ``ri:``, ``icfs:``, extension prefixes and values like ``dc=example`` stay intact.

    - ``c:attributes/ri:emptype``              → ``attributes/ri:emptype``
    - ``c:activation/c:administrativeStatus``  → ``activation/administrativeStatus``
    - ``c:name``                               → ``name``
    - ``c:UserType``                           → ``UserType``
    - ``attributes/ri:emptype``                → unchanged
    - ``extension/ext:personalNumber``         → unchanged
    - ``ri:account``                           → unchanged

    :param path: Item path or attribute name; non-string values are returned as-is.
    :return: Path without ``c:`` prefixes.
    """
    if isinstance(path, str):
        return _COMMON_NS_PREFIX_PATTERN.sub("", path)
    return path


def normalize_attr_name_for_mel(name: str) -> str:
    """
    Normalize a namespaced MidPoint attribute name into a valid MEL identifier.

    MidPoint attribute names may carry namespace prefixes (e.g.
    ``extension/ext:personalNumber``, ``attributes/ri:username``) which are
    invalid as MEL variable names because ``:`` is not a legal identifier
    character. MidPoint resolves the same attributes without the prefix, so
    stripping it is safe.

    The rule: take the substring after the **last** ``:`` in the name. This
    correctly handles all known patterns:

    - ``name``                         → ``name``
    - ``givenName``                    → ``givenName``
    - ``extension/ext:personalNumber`` → ``personalNumber``
    - ``attributes/ri:username``       → ``username``
    - ``attributes/icfs:name``         → ``name``
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
    :raises InvalidValueException: If the value is invalid for the given type, or the type is unsupported.
    """
    v = raw.strip()
    t = type_str.strip().lower()

    if t == "xsd:boolean":
        val = v.lower()
        if val == "true" or val == "false":
            return val
        raise InvalidValueException(f"Expected 'true' or 'false' for boolean, got {raw!r}")

    if t == "xsd:string":
        return f'"{v}"'

    if t in ("xsd:int", "xsd:long"):
        try:
            int(v)  # Check if it's a valid integer.
            return v
        except InvalidValueException:
            raise InvalidValueException(f"Invalid integer {raw!r} for type {type_str}")

    if t in ("xsd:double", "xsd:float"):
        try:
            float(v)  # Check if it's a valid float
            return v
        except InvalidValueException:
            raise InvalidValueException(f"Invalid float {raw!r} for type {type_str}")

    if t == "xsd:datetime":
        try:
            datetime.fromisoformat(v)  # Check if it's a valid datetime in iso format
            return v
        except Exception as e:
            raise InvalidValueException(f"Invalid datetime {raw!r}: {e}") from e

    raise InvalidValueException(f"Unsupported XSD type: {type_str!r}")


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

    raise InvalidValueException(
        f"Expected single non-multivalued value for type {type_str}, got list of length {len(parsed_list)}"
    )


def pretty_json(value: Any) -> str:
    """
    Serialize a Python object into a human-readable JSON string.

    Uses UTF-8-friendly output (ensure_ascii=False) and 2-space indentation.
    """

    return json.dumps(value, ensure_ascii=False, indent=2)


def is_null_script(script: str | None) -> bool:
    """
    Return True when an LLM response did not contain executable MEL.
    """
    if script is None:
        return True
    normalized = re.sub(r"//.*", "", script)
    normalized = normalized.strip()
    return not normalized or normalized == "null" or normalized == "return null"


def get_version_info():
    """
    Returns version name including git commit if available.
    """
    git_commit = config.app.git_commit
    version = config.app.version
    commit_info = f" ({git_commit})" if git_commit else ""
    return f"{version}{commit_info}"
