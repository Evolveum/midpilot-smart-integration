# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from datetime import datetime, timezone

import pytest

from src.utils import parse_value_by_type, to_groovy_literal


# ---- to_groovy_literal / parse_value_by_type focused tests ----
@pytest.mark.parametrize(
    "value, expected",
    [
        (1, "1"),
        (3.14, "3.14"),
        (True, "true"),
        (False, "false"),
        (None, "null"),
        ("simple", '"simple"'),
        ("O'Reilly", '"O\'Reilly"'),
        ("back\\slash", r'"back\\slash"'),
        ("line\nbreak", '"line\\nbreak"'),
    ],
)
def test_to_groovy_literal_primitives_and_escaping(value, expected):
    assert to_groovy_literal(value) == expected


def test_to_groovy_literal_list_and_nested():
    assert to_groovy_literal([1, "a", False]) == '[1, "a", false]'

    nested = {"outer": [1, "a", False], "x": "y"}
    expected = '["outer": [1, "a", false], "x": "y"]'
    assert to_groovy_literal(nested) == expected


def test_to_groovy_literal_dict_simple():
    d = {"k": "v", "n": 5}
    assert to_groovy_literal(d) == '["k": "v", "n": 5]'


def test_to_groovy_literal_datetime_utc():
    dt = datetime(2023, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    lit = to_groovy_literal(dt)
    assert lit.startswith("Date.parse(")
    assert ("2023-01-02T03:04:05Z" in lit) or ("2023-01-02T03:04:05+00:00" in lit)


def test_parse_value_by_type_single_and_multivalued():
    # single-valued
    assert parse_value_by_type(["42"], "xsd:int", multivalued=False) == 42
    assert parse_value_by_type(["true"], "xsd:boolean", multivalued=False) is True
    assert parse_value_by_type(["false"], "xsd:boolean", multivalued=False) is False
    assert parse_value_by_type(["hello"], "xsd:string", multivalued=False) == "hello"
    dt = parse_value_by_type(["2023-01-02T03:04:05"], "xsd:dateTime", multivalued=False)
    assert isinstance(dt, datetime)
    assert dt == datetime.fromisoformat("2023-01-02T03:04:05")

    # multivalued
    assert parse_value_by_type(["1", "2", "3"], "xsd:int", multivalued=True) == [1, 2, 3]
    assert parse_value_by_type(["true", "false"], "xsd:boolean", multivalued=True) == [True, False]

    # error cases
    with pytest.raises(ValueError):
        parse_value_by_type(["A", "B"], "xsd:string", multivalued=False)  # multiple for single-valued
    with pytest.raises(ValueError):
        parse_value_by_type(["yes"], "xsd:boolean", multivalued=False)
    with pytest.raises(ValueError):
        parse_value_by_type(["notanint"], "xsd:int", multivalued=False)
    with pytest.raises(ValueError):
        parse_value_by_type(["2023-99-99"], "xsd:dateTime", multivalued=False)
