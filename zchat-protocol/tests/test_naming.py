from zchat_protocol.naming import scoped_name, AGENT_SEPARATOR


def test_separator_is_dash():
    assert AGENT_SEPARATOR == "-"


def test_scoped_name_adds_prefix():
    assert scoped_name("helper", "alice") == "alice-helper"


def test_scoped_name_no_double_prefix():
    assert scoped_name("alice-helper", "alice") == "alice-helper"


def test_scoped_name_different_prefix():
    assert scoped_name("bob-helper", "alice") == "bob-helper"
