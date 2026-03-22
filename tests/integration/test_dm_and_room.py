"""Integration test: DM routing and room @mention filtering."""

import json
import time
import pytest

from message import detect_mention, clean_mention, make_dm_pair

pytestmark = pytest.mark.integration


@pytest.fixture
def zenoh_session():
    import zenoh

    config = zenoh.Config()
    config.insert_json5("mode", '"peer"')
    session = zenoh.open(config)
    yield session
    session.close()


class TestDmRouting:
    def test_agent_receives_own_dm(self, zenoh_session):
        """Messages to alice:agent0's DM pair are received."""
        pair = make_dm_pair("alice:agent0", "bob")
        topic = f"wc/dm/{pair}/messages"
        received = []

        zenoh_session.declare_subscriber(
            topic,
            lambda s: received.append(json.loads(s.payload.to_string())),
            background=True,
        )
        time.sleep(0.5)

        zenoh_session.put(topic, json.dumps({
            "id": "r-001", "nick": "bob", "type": "msg",
            "body": "hello", "ts": time.time(),
        }))

        deadline = time.time() + 2.0
        while not received and time.time() < deadline:
            time.sleep(0.1)

        assert len(received) == 1

    def test_other_agent_does_not_receive_dm(self, zenoh_session):
        """bob:agent1 should not receive DMs addressed to alice:agent0."""
        target_pair = make_dm_pair("alice:agent0", "carol")
        target_topic = f"wc/dm/{target_pair}/messages"

        other_received = []

        def other_filter(sample):
            key = str(sample.key_expr)
            pair = key.split("/")[2]
            if "bob:agent1" in pair.split("_"):
                other_received.append(True)

        zenoh_session.declare_subscriber(
            "wc/dm/*/messages", other_filter, background=True
        )
        time.sleep(0.5)

        zenoh_session.put(target_topic, json.dumps({
            "id": "r-002", "nick": "carol", "type": "msg",
            "body": "for alice:agent0 only", "ts": time.time(),
        }))

        time.sleep(1.0)
        assert len(other_received) == 0


class TestRoomMentionFiltering:
    def test_mention_triggers_forwarding(self):
        """Room message with @alice:agent0 should be forwarded."""
        body = "@alice:agent0 list files"
        assert detect_mention(body, "alice:agent0") is True
        cleaned = clean_mention(body, "alice:agent0")
        assert cleaned == "list files"

    def test_no_mention_not_forwarded(self):
        """Room message without @mention should not be forwarded."""
        body = "hello everyone, nice day"
        assert detect_mention(body, "alice:agent0") is False

    def test_wrong_agent_mention_not_forwarded(self):
        """@bob:agent1 mention should not trigger alice:agent0."""
        body = "@bob:agent1 do something"
        assert detect_mention(body, "alice:agent0") is False

    def test_mention_in_room_roundtrip(self, zenoh_session):
        """End-to-end: room message with @mention is received and cleaned."""
        topic = "wc/rooms/general/messages"
        agent_name = "alice:agent0"
        forwarded = []

        def room_handler(sample):
            msg = json.loads(sample.payload.to_string())
            if msg.get("nick") == agent_name:
                return
            body = msg.get("body", "")
            if detect_mention(body, agent_name):
                msg["body"] = clean_mention(body, agent_name)
                forwarded.append(msg)

        zenoh_session.declare_subscriber(
            topic, room_handler, background=True
        )
        time.sleep(0.5)

        zenoh_session.put(topic, json.dumps({
            "id": "rm-001", "nick": "carol", "type": "msg",
            "body": "@alice:agent0 what files changed?", "ts": time.time(),
        }))

        deadline = time.time() + 2.0
        while not forwarded and time.time() < deadline:
            time.sleep(0.1)

        assert len(forwarded) == 1
        assert forwarded[0]["body"] == "what files changed?"
