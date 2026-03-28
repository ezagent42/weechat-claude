from zchat_protocol.sys_messages import (
    is_sys_message, make_sys_message,
    encode_sys_for_irc, decode_sys_from_irc,
    IRC_SYS_PREFIX,
)


def test_sys_prefix():
    assert IRC_SYS_PREFIX == "__zchat_sys:"


def test_make_sys_message_fields():
    msg = make_sys_message("alice-agent0", "sys.stop_request", {"reason": "test"})
    assert msg["nick"] == "alice-agent0"
    assert msg["type"] == "sys.stop_request"
    assert msg["body"]["reason"] == "test"
    assert "id" in msg
    assert "ts" in msg


def test_is_sys_message():
    assert is_sys_message({"type": "sys.stop_request"})
    assert not is_sys_message({"type": "msg"})


def test_irc_roundtrip():
    msg = make_sys_message("alice-agent0", "sys.stop_request", {"reason": "test"})
    encoded = encode_sys_for_irc(msg)
    assert encoded.startswith("__zchat_sys:")
    decoded = decode_sys_from_irc(encoded)
    assert decoded["type"] == "sys.stop_request"
    assert decoded["body"]["reason"] == "test"


def test_decode_non_sys():
    assert decode_sys_from_irc("hello world") is None
    assert decode_sys_from_irc("{json-like}") is None
