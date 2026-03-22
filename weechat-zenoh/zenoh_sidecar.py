#!/usr/bin/env python3
"""
Zenoh sidecar process for weechat-zenoh plugin.
Runs as standalone process to avoid PyO3 subinterpreter issues.
Communicates via stdin (JSON commands) / stdout (JSON events).
"""

import json
import sys
import uuid
import time
from collections import deque

# Support --mock flag for testing
_use_mock = "--mock" in sys.argv

if _use_mock:
    from conftest import MockZenohSession
else:
    import zenoh

ZENOH_DEFAULT_ENDPOINT = "tcp/127.0.0.1:7447"

# --- Global state ---
session = None
my_nick = ""
publishers = {}          # key → zenoh.Publisher
subscribers = {}         # key → zenoh.Subscriber
liveliness_subs = {}     # key → zenoh liveliness Subscriber
liveliness_tokens = {}   # key → zenoh.LivelinessToken
channels = set()
privates = set()
event_queue = deque()    # events to write to stdout


def emit(event: dict):
    """Write JSON event to stdout (thread-safe via deque)."""
    event_queue.append(event)


def flush_events():
    """Write all queued events to stdout. Call from main thread."""
    while True:
        try:
            event = event_queue.popleft()
        except IndexError:
            break
        sys.stdout.write(json.dumps(event) + "\n")
        sys.stdout.flush()


def build_config(connect: str | None = None):
    """Build Zenoh client config."""
    config = zenoh.Config()
    config.insert_json5("mode", '"client"')
    endpoints = connect.split(",") if connect else [ZENOH_DEFAULT_ENDPOINT]
    config.insert_json5("connect/endpoints", json.dumps(endpoints))
    return config


def handle_init(params: dict):
    global session, my_nick
    my_nick = params["nick"]
    connect = params.get("connect")

    if _use_mock:
        session = MockZenohSession()
        zid = "mock-zid-" + uuid.uuid4().hex[:8]
    else:
        config = build_config(connect)
        session = zenoh.open(config)
        zid = str(session.info.zid())

    # Global liveliness
    liveliness_tokens["_global"] = \
        session.liveliness().declare_token(f"wc/presence/{my_nick}")

    emit({"event": "ready", "zid": zid})


def handle_command(cmd: dict):
    """Dispatch a single command."""
    name = cmd.get("cmd")
    if name == "init":
        handle_init(cmd)
    else:
        emit({"event": "error", "detail": f"Unknown command: {name}"})


def main():
    """Main loop: read stdin line by line, dispatch commands."""
    # Use readline() to avoid buffered iteration blocking
    for line in iter(sys.stdin.readline, ""):
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError as e:
            emit({"event": "error", "detail": f"Invalid JSON: {e}"})
            flush_events()
            continue
        handle_command(cmd)
        flush_events()

    # stdin EOF — clean up
    cleanup()


def cleanup():
    global session
    for token in liveliness_tokens.values():
        token.undeclare()
    for sub in liveliness_subs.values():
        sub.undeclare()
    for sub in subscribers.values():
        sub.undeclare()
    for pub in publishers.values():
        pub.undeclare()
    if session and not _use_mock:
        session.close()
    session = None


if __name__ == "__main__":
    main()
