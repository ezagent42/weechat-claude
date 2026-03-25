"""Integration test: sys message round-trip over real Zenoh."""
import json
import time
import pytest
from wc_protocol.sys_messages import make_sys_message, is_sys_message
from wc_protocol.topics import private_topic, make_private_pair


@pytest.mark.integration
def test_sys_ping_pong_roundtrip(zenoh_session):
    """Send sys.ping on a private topic, verify it arrives."""
    pair = make_private_pair("test_user", "test_agent")
    topic = private_topic(pair)

    received = []

    def on_sample(sample):
        msg = json.loads(sample.payload.to_string())
        if is_sys_message(msg):
            received.append(msg)

    sub = zenoh_session.declare_subscriber(topic, on_sample)

    ping = make_sys_message("test_user", "sys.ping", {})
    zenoh_session.put(topic, json.dumps(ping).encode())

    # Wait for delivery
    deadline = time.time() + 5
    while not received and time.time() < deadline:
        time.sleep(0.1)

    sub.undeclare()

    assert len(received) == 1
    assert received[0]["type"] == "sys.ping"
    assert received[0]["nick"] == "test_user"
