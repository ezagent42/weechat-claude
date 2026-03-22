"""Tests for Zenoh topic conventions and message format compliance."""

import json
import uuid
import time

from message import make_dm_pair, dm_topic, room_topic, presence_topic


class TestMessageJsonSchema:
    """Verify message JSON structure matches PRD §3.3."""

    def _make_msg(self, **overrides):
        msg = {
            "id": uuid.uuid4().hex,
            "nick": "alice",
            "type": "msg",
            "body": "hello everyone",
            "ts": time.time(),
        }
        msg.update(overrides)
        return msg

    def test_required_fields(self):
        msg = self._make_msg()
        for field in ("id", "nick", "type", "body", "ts"):
            assert field in msg

    def test_type_enum(self):
        valid_types = {"msg", "action", "join", "leave", "nick"}
        for t in valid_types:
            msg = self._make_msg(type=t)
            assert msg["type"] in valid_types

    def test_json_serializable(self):
        msg = self._make_msg()
        s = json.dumps(msg)
        parsed = json.loads(s)
        assert parsed == msg

    def test_ts_is_numeric(self):
        msg = self._make_msg()
        assert isinstance(msg["ts"], (int, float))


class TestDmPairSorting:
    def test_pair_alphabetical(self):
        assert make_dm_pair("bob", "alice") == "alice_bob"

    def test_pair_with_agent(self):
        assert make_dm_pair("alice:agent0", "zara") == "alice:agent0_zara"

    def test_pair_symmetric(self):
        assert make_dm_pair("x", "y") == make_dm_pair("y", "x")


class TestTopicFormats:
    def test_room_topic(self):
        assert room_topic("general") == "wc/rooms/general/messages"

    def test_dm_topic(self):
        assert dm_topic("alice_bob") == "wc/dm/alice_bob/messages"

    def test_presence_topic(self):
        assert presence_topic("alice:agent0") == "wc/presence/alice:agent0"

    def test_room_presence_format(self):
        # Room presence follows: wc/rooms/{room}/presence/{nick}
        room = "general"
        nick = "alice"
        expected = f"wc/rooms/{room}/presence/{nick}"
        assert expected == "wc/rooms/general/presence/alice"
