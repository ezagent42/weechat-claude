"""Integration test: Channel server bridge (Zenoh -> MCP -> reply -> Zenoh).

Tests the channel server's message routing logic with a real Zenoh session
but mocked MCP transport.
"""

import json
import os
import time
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def zenoh_session():
    """Create a single Zenoh peer session."""
    import zenoh

    config = zenoh.Config()
    config.insert_json5("mode", '"peer"')
    session = zenoh.open(config)
    yield session
    session.close()


class TestChannelBridge:
    def test_private_received_by_agent(self, zenoh_session):
        """Publish a private message and verify the agent's filter logic accepts it."""
        from message import make_private_pair

        agent_name = "agent0"
        sender = "alice"
        pair = make_private_pair(agent_name, sender)
        topic = f"wc/private/{pair}/messages"

        received = []
        # Simulate the agent's private filter
        def filter_private(sample):
            key = str(sample.key_expr)
            parts = key.split("/")
            if len(parts) >= 3:
                p = parts[2]
                if agent_name in p.split("_"):
                    msg = json.loads(sample.payload.to_string())
                    if msg.get("nick") != agent_name:
                        received.append(msg)

        zenoh_session.declare_subscriber(
            "wc/private/*/messages", filter_private, background=True
        )
        time.sleep(0.5)

        msg = {
            "id": "bridge-001",
            "nick": sender,
            "type": "msg",
            "body": "hello agent",
            "ts": time.time(),
        }
        zenoh_session.put(topic, json.dumps(msg))

        deadline = time.time() + 2.0
        while not received and time.time() < deadline:
            time.sleep(0.1)

        assert len(received) == 1
        assert received[0]["body"] == "hello agent"

    def test_private_not_for_agent_ignored(self, zenoh_session):
        """Privates between other users should not be received by agent."""
        agent_name = "agent0"

        received = []
        def filter_private(sample):
            key = str(sample.key_expr)
            parts = key.split("/")
            if len(parts) >= 3:
                p = parts[2]
                if agent_name in p.split("_"):
                    received.append(True)

        zenoh_session.declare_subscriber(
            "wc/private/*/messages", filter_private, background=True
        )
        time.sleep(0.5)

        # Private between alice and bob -- agent0 not involved
        msg = json.dumps({
            "id": "other-001",
            "nick": "alice",
            "type": "msg",
            "body": "hey bob",
            "ts": time.time(),
        })
        zenoh_session.put("wc/private/alice_bob/messages", msg)

        time.sleep(1.0)
        assert len(received) == 0

    def test_reply_publishes_to_zenoh(self, zenoh_session):
        """Verify the reply tool publishes correctly formatted messages."""
        received = []
        zenoh_session.declare_subscriber(
            "wc/channels/general/messages",
            lambda s: received.append(json.loads(s.payload.to_string())),
            background=True,
        )
        time.sleep(0.5)

        # Simulate what the reply tool does
        agent_name = "agent0"
        reply_msg = json.dumps({
            "id": os.urandom(8).hex(),
            "nick": agent_name,
            "type": "msg",
            "body": "Here are the files",
            "ts": time.time(),
        })
        zenoh_session.put("wc/channels/general/messages", reply_msg)

        deadline = time.time() + 2.0
        while not received and time.time() < deadline:
            time.sleep(0.1)

        assert len(received) == 1
        assert received[0]["nick"] == "agent0"
        assert received[0]["body"] == "Here are the files"
