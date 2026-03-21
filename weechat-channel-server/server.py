#!/usr/bin/env python3
"""
weechat-channel-server: Claude Code Channel MCP Server
桥接 Zenoh 消息总线 ↔ Claude Code MCP stdio 协议

This is a Claude Code plugin that runs as an MCP server (stdio transport).
It receives messages from Zenoh and injects them into Claude Code as
channel notifications, and provides a reply tool for Claude to respond.
"""

import json
import sys
import os

AGENT_NAME = os.environ.get("AGENT_NAME", "agent0")


def main():
    import zenoh
    from mcp.server.fastmcp import FastMCP

    from message import MessageDedup, detect_mention, clean_mention, make_dm_pair
    from tools import register_tools

    # ============================================================
    # Zenoh 初始化
    # ============================================================

    zenoh_config = zenoh.Config()
    zenoh_config.insert_json5("mode", '"peer"')

    connect = os.environ.get("ZENOH_CONNECT")
    if connect:
        zenoh_config.insert_json5("connect/endpoints",
                                  json.dumps(connect.split(",")))

    zenoh_session = zenoh.open(zenoh_config)

    # 在线状态
    zenoh_session.liveliness().declare_token(f"wc/presence/{AGENT_NAME}")

    # Message deduplication
    dedup = MessageDedup()

    # ============================================================
    # MCP Server
    # ============================================================

    mcp = FastMCP(
        name=f"weechat-channel-{AGENT_NAME}",
        instructions=(
            f'You are "{AGENT_NAME}", a coding assistant connected to a '
            f"WeeChat chat system via Zenoh P2P messaging.\n"
            f"Messages arrive as <channel> events. Each event has a sender "
            f"and a context (DM or #room).\n"
            f"The sender reads WeeChat, not this session. Anything you want "
            f"them to see must go through the reply tool.\n"
            f"Always use the reply tool to respond."
        ),
    )

    # Register tools
    register_tools(mcp, zenoh_session)

    # ============================================================
    # Zenoh → Claude Code 桥接
    # ============================================================

    def _inject_to_claude(msg: dict, context: str):
        """Inject a message as a channel notification into Claude Code.

        Uses MCP server notification mechanism to deliver messages
        as <channel> events that Claude Code processes.
        """
        sender = msg.get("nick", "unknown")
        body = msg.get("body", "")
        msg_id = msg.get("id", "")

        # Deduplication
        if msg_id and dedup.is_duplicate(msg_id):
            return

        print(
            f"[channel-server] [{context}] {sender}: {body}",
            file=sys.stderr,
        )

        # Send as MCP notification
        # The FastMCP server's internal session handles this
        # TODO: Validate the exact notification method once
        # Claude Code's channel API is finalized.
        # For now, we use the pattern from feishu-claude-code-channel:
        # server.send_notification() with channel event payload

    def on_dm_message(sample):
        """DM 消息到达 → 注入 Claude Code session"""
        try:
            msg = json.loads(sample.payload.to_string())
            if msg.get("nick") == AGENT_NAME:
                return
            sender = msg.get("nick", "unknown")
            _inject_to_claude(msg, f"DM from {sender}")
        except Exception as e:
            print(f"[channel-server] DM error: {e}", file=sys.stderr)

    def on_room_message(sample):
        """Room 消息到达 → 检查 @mention → 注入 Claude Code"""
        try:
            msg = json.loads(sample.payload.to_string())
            if msg.get("nick") == AGENT_NAME:
                return
            body = msg.get("body", "")
            if not detect_mention(body, AGENT_NAME):
                return
            # Clean the @mention from body
            msg["body"] = clean_mention(body, AGENT_NAME)
            room = str(sample.key_expr).split("/")[2]
            _inject_to_claude(msg, f"#{room}")
        except Exception as e:
            print(f"[channel-server] Room error: {e}", file=sys.stderr)

    # Subscribe to DMs containing this agent's name
    def _filter_dm(sample):
        """Only process DM pairs that include this agent."""
        key = str(sample.key_expr)
        # key format: wc/dm/{pair}/messages
        parts = key.split("/")
        if len(parts) >= 3:
            pair = parts[2]
            if AGENT_NAME in pair.split("_"):
                on_dm_message(sample)

    zenoh_session.declare_subscriber(
        "wc/dm/*/messages",
        _filter_dm,
        background=True,
    )

    # Subscribe to all rooms (filter by @mention in handler)
    zenoh_session.declare_subscriber(
        "wc/rooms/*/messages",
        on_room_message,
        background=True,
    )

    # Publish ready status
    zenoh_session.put(
        f"wc/presence/{AGENT_NAME}",
        json.dumps({"status": "ready"}),
    )

    print(f"[channel-server] {AGENT_NAME} ready on Zenoh", file=sys.stderr)

    # ============================================================
    # 启动 MCP server (stdio)
    # ============================================================

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
