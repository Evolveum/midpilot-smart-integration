# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import pytest

from src.utils import normalize_attr_name_for_mel, quote_by_type


def test_quote_by_type_single_and_multivalued():
    # single-valued
    assert quote_by_type(["42"], "xsd:int", multivalued=False) == "42"
    assert quote_by_type(["true"], "xsd:boolean", multivalued=False) == "true"
    assert quote_by_type(["false"], "xsd:boolean", multivalued=False) == "false"
    assert quote_by_type(["hello"], "xsd:string", multivalued=False) == '"hello"'
    assert quote_by_type(["2023-01-02T03:04:05.000"], "xsd:dateTime", multivalued=False) == "2023-01-02T03:04:05.000"
    assert quote_by_type(["2023-01-02T03:04:05.000"], "xsd:string", multivalued=False) == '"2023-01-02T03:04:05.000"'

    # multivalued
    assert quote_by_type(["1", "2", "3"], "xsd:int", multivalued=True) == ["1", "2", "3"]
    assert quote_by_type(["true", "false"], "xsd:boolean", multivalued=True) == ["true", "false"]

    # error cases
    with pytest.raises(ValueError):
        quote_by_type(["A", "B"], "xsd:string", multivalued=False)  # multiple for single-valued
    with pytest.raises(ValueError):
        quote_by_type(["yes"], "xsd:boolean", multivalued=False)
    with pytest.raises(ValueError):
        quote_by_type(["notanint"], "xsd:int", multivalued=False)
    with pytest.raises(ValueError):
        quote_by_type(["2023-99-99"], "xsd:dateTime", multivalued=False)


# ---- normalize_attr_name_for_groovy tests ----
@pytest.mark.parametrize(
    "raw_name, expected",
    [
        # Colon-separated (namespace prefix)
        ("c:name", "name"),
        ("c:givenName", "givenName"),
        ("c:familyName", "familyName"),
        ("c:extension/ext:personalNumber", "personalNumber"),
        ("c:attributes/ri:username", "username"),
        ("c:attributes/icfs:name", "name"),
        ("ext:employeeNumber", "employeeNumber"),
        # Slash-separated (path without namespace)
        ("attributes/username", "username"),
        ("extension/personalNumber", "personalNumber"),
        ("activation/administrativeStatus", "administrativeStatus"),
        # Simple names (no separator)
        ("givenName", "givenName"),
        ("personalNumber", "personalNumber"),
        ("name", "name"),
    ],
)
def test_normalize_attr_name_for_mel(raw_name, expected):
    assert normalize_attr_name_for_mel(raw_name) == expected
