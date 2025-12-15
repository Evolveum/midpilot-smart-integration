# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import json
from datetime import datetime
from typing import Any


# ---- parsing / normalization utilities ----
def _parse_single_by_type(raw: str, type_str: str) -> Any:
    """
    Parse a single raw string into a Python object according to the given xsd type.

    :param raw: The raw string representation of the value.
    :param type_str: The XSD type string (e.g., "xsd:int", "xsd:datetime").
    :return: The parsed Python value.
    :raises ValueError: If the value is invalid for the given type, or the type is unsupported.
    """
    v = raw.strip()
    t = type_str.strip().lower()

    if t == "xsd:boolean":
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        raise ValueError(f"Expected 'true' or 'false' for boolean, got {raw!r}")

    if t == "xsd:string":
        return v

    if t in ("xsd:int", "xsd:long"):
        try:
            return int(v)
        except ValueError:
            raise ValueError(f"Invalid integer {raw!r} for type {type_str}")

    if t in ("xsd:double", "xsd:float"):
        try:
            return float(v)
        except ValueError:
            raise ValueError(f"Invalid float {raw!r} for type {type_str}")

    if t == "xsd:datetime":
        try:
            return datetime.fromisoformat(v)
        except Exception as e:
            raise ValueError(f"Invalid datetime {raw!r}: {e}") from e

    raise ValueError(f"Unsupported XSD type: {type_str!r}")


def parse_value_by_type(raw: Any, type_str: str, multivalued: bool = False) -> Any:
    """
    Convert input (expected to be a list, possibly empty) into Python value(s) based on the xsd type.

    Empty list normalizes to None (if not multivalued) or [] (if multivalued).

    :param raw: The incoming raw value; expected to be a list or None.
    :param type_str: The XSD type string (e.g., "xsd:string", "xsd:int").
    :param multivalued: Whether the target schema allows multiple values.
    :return: Parsed value: single scalar (if not multivalued), list (if multivalued), or None for empties.
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
            parsed_list.append(_parse_single_by_type(str(item), type_str))

    if multivalued:
        return parsed_list
    if len(parsed_list) == 1:
        return parsed_list[0]
    raise ValueError(
        f"Expected single non-multivalued value for type {type_str}, got list of length {len(parsed_list)}"
    )


def to_groovy_literal(value: Any) -> str:
    """
    Serialize a Python value into a valid Groovy literal.
    Strings are emitted as double-quoted literals (JSON-escaped).

    Supported types: datetime, str, bool, None, int, float, list, dict.
    """

    if isinstance(value, datetime):
        # ISO 8601; Date.parse uses Java SimpleDateFormat.
        return f"Date.parse(\"yyyy-MM-dd'T'HH:mm:ssX\", {json.dumps(value.isoformat())})"

    if isinstance(value, str):
        return json.dumps(value)

    if value is None or isinstance(value, (bool, int, float)):
        return json.dumps(value)

    if isinstance(value, list):
        inner = ", ".join(to_groovy_literal(v) for v in value)
        return f"[{inner}]"

    if isinstance(value, dict):
        pairs = []
        for k, v in value.items():
            if isinstance(k, str):
                key_literal = json.dumps(k)
            else:
                key_literal = f"({to_groovy_literal(k)})"
            pairs.append(f"{key_literal}: {to_groovy_literal(v)}")
        return f"[{', '.join(pairs)}]"

    return json.dumps(str(value))


def pretty_json(value: Any) -> str:
    """
    Serialize a Python object into a human-readable JSON string.

    Uses UTF-8-friendly output (ensure_ascii=False) and 2-space indentation.
    """

    return json.dumps(value, ensure_ascii=False, indent=2)
