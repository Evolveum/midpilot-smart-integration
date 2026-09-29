# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import pytest

from src.utils import normalize_attr_name_for_mel, quote_by_type, strip_common_prefix


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
        ("name", "name"),
        ("givenName", "givenName"),
        ("familyName", "familyName"),
        ("extension/ext:personalNumber", "personalNumber"),
        ("attributes/ri:username", "username"),
        ("attributes/icfs:name", "name"),
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


# ---- strip_common_prefix tests ----
@pytest.mark.parametrize(
    "raw_path, expected",
    [
        # Legacy c:-prefixed forms
        ("c:attributes/ri:emptype", "attributes/ri:emptype"),
        ("c:activation/c:administrativeStatus", "activation/administrativeStatus"),
        ("c:credentials/c:password/c:value", "credentials/password/value"),
        ("c:name", "name"),
        ("c:UserType", "UserType"),
        ("c:extension/ext:personalNumber", "extension/ext:personalNumber"),
        ("c:attributes/ri:dn = ou=projects,dc=example,dc=com", "attributes/ri:dn = ou=projects,dc=example,dc=com"),
        # Already plain / other prefixes stay untouched
        ("attributes/ri:emptype", "attributes/ri:emptype"),
        ("extension/ext:personalNumber", "extension/ext:personalNumber"),
        ("ri:account", "ri:account"),
        ("name", "name"),
        ("UserType", "UserType"),
        ("dc=example,dc=com", "dc=example,dc=com"),
    ],
)
def test_strip_common_prefix(raw_path, expected):
    assert strip_common_prefix(raw_path) == expected


def test_strip_common_prefix_non_string():
    assert strip_common_prefix(None) is None
    assert strip_common_prefix(42) == 42


def test_midpoint_schema_name_accepts_legacy_prefixed_focus_type():
    from src.common.schema import FocusType, MidpointSchema

    for raw_name in ("c:UserType", "UserType"):
        schema = MidpointSchema(name=raw_name, description=None, attribute=[])
        assert schema.name == FocusType.UserType


def test_statistics_refs_accept_legacy_prefixed_paths():
    from src.modules.object_type.schema import AttributeStat, AttributeTupleStat

    stat = AttributeStat(ref="c:attributes/ri:groupType", uniqueValueCount=4, missingValueCount=0)
    assert stat.ref == "attributes/ri:groupType"

    tuple_stat = AttributeTupleStat(ref=["c:attributes/ri:a", "c:activation/c:administrativeStatus"], tupleCount=None)
    assert tuple_stat.ref == ("attributes/ri:a", "activation/administrativeStatus")
