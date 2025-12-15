# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import pytest

from src.common.schema import ApplicationSchema, BaseSchemaAttribute, FocusType, MidpointSchema
from src.modules.utils import clean_description

real_email_description = '<xsd:documentation xmlns:xsd="http://www.w3.org/2001/XMLSchema">\r\n                                    \r\n    <p>\r\n                                    E-Mail address of the user, org. unit, etc. This is the address\r\n                                    supposed to be used for communication with the\r\n                                    user, org. unit, etc. E.g. IDM system may send notifications\r\n                                    to the e-mail address. It is NOT supposed to be\r\n                                    full-featured e-mail address data structure\r\n                                    e.g. for the purpose of complex address-book application.\r\n                                </p>\r\n                                \r\n</xsd:documentation>\r\n'


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        # Basic HTML tag removal
        ("<b>Hello</b> world", "Hello world"),
        ("<p>Some text</p>", "Some text"),
        ('<div class="x">Hello</div>', "Hello"),
        ('<div    class="x"  >Hello</div>', "Hello"),
        ("<c:UserType>Example</c:UserType>", "Example"),
        # Mathematical comparisons should remain untouched
        ("x>2 and a<b", "x>2 and a<b"),
        ("x<a and a>b", "x<a and a>b"),
        ("if a <= b then a >= 2", "if a <= b then a >= 2"),
        ("Temperature is < 20°C", "Temperature is < 20°C"),
        # Whitespace normalization
        ("Hello     world", "Hello world"),
        ("\nHello \t world\n", "Hello world"),
        # Mixed HTML tags and mathematical symbols
        ("<b>x > 2</b> and <i>a < b</i>", "x > 2 and a < b"),
        # Edge cases
        ("", ""),
        (None, ""),
        # More copmlex examples
        (
            real_email_description,
            "E-Mail address of the user, org. unit, etc. This is the address supposed to be used for communication with the user, org. unit, etc. E.g. IDM system may send notifications to the e-mail address. It is NOT supposed to be full-featured e-mail address data structure e.g. for the purpose of complex address-book application.",
        ),
        (
            """
            <h4 class="xyz">
                formula:
                <br>
                a > b and b < c
                <hr/>
                <br />
                a<b and b>c
            </h4>
            """,
            "formula: a > b and b < c a<b and b>c",
        ),
    ],
)
def test_clean_description(input_text, expected_output):
    assert clean_description(input_text) == expected_output


def test_application_schema_description_is_cleaned():
    attrs = [
        BaseSchemaAttribute(
            name="phone", type="xsd:string", description="<b>Contact</b> number", minOccurs=0, maxOccurs=1
        ),
        BaseSchemaAttribute(name="math", type="xsd:string", description="x>2 and a<b", minOccurs=0, maxOccurs=1),
    ]

    app = ApplicationSchema(
        name="account",
        description="<p>Contains <i>user</i> accounts</p>",
        attribute=attrs,
    )

    assert app.description == "Contains user accounts"
    assert app.attribute[0].description == "Contact number"
    assert app.attribute[1].description == "x>2 and a<b"


def test_midpoint_schema_description_is_cleaned_with_namespace():
    mp = MidpointSchema(
        name=FocusType.UserType,
        description="<c:UserType>User type entity</c:UserType>",
        attribute=[
            BaseSchemaAttribute(
                name="cn", type="xsd:string", description="Common <i>name</i>", minOccurs=0, maxOccurs=1
            )
        ],
    )
    assert mp.description == "User type entity"
    assert mp.attribute[0].description == "Common name"


def test_no_description_fields_are_unchanged():
    assert clean_description(None) == ""

    a = BaseSchemaAttribute(name="x", type="xsd:string", description=None, minOccurs=0, maxOccurs=1)
    assert a.description is None

    s = ApplicationSchema(name="foo", description=None, attribute=[])
    assert s.description is None
    assert s.attribute == []
