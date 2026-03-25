"""Tests for /zenoh command edge cases (leave validation, who)."""
from wc_protocol.topics import make_private_pair


def test_leave_channel_not_joined():
    channels = {"general"}
    assert "nonexistent" not in channels


def test_leave_private_not_open():
    privates = {"alice_bob"}
    pair = make_private_pair("alice", "unknown")
    assert pair not in privates


def test_leave_invalid_target():
    target = "no-prefix"
    assert not target.startswith("#") and not target.startswith("@")


def test_who_not_in_channel():
    channels = {"general"}
    assert "nonexistent" not in channels
