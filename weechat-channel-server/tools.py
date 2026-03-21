"""
MCP tool definitions for weechat-channel-server.
Provides reply capability for Claude Code to send messages back to WeeChat.
"""

import json
import os
import time

from message import chunk_message

AGENT_NAME = os.environ.get("AGENT_NAME", "agent0")


def register_tools(mcp, zenoh_session):
    """Register MCP tools on the FastMCP server instance."""

    @mcp.tool()
    async def reply(chat_id: str, text: str) -> str:
        """Reply to a WeeChat user or room.

        Args:
            chat_id: Target — a username for DM (e.g. "alice")
                     or a #room name (e.g. "#general")
            text: Message content
        """
        chunks = chunk_message(text)

        for chunk in chunks:
            msg = json.dumps({
                "id": os.urandom(8).hex(),
                "nick": AGENT_NAME,
                "type": "msg",
                "body": chunk,
                "ts": time.time()
            })

            if chat_id.startswith("#"):
                room = chat_id.lstrip("#")
                zenoh_session.put(f"wc/rooms/{room}/messages", msg)
            else:
                pair = "_".join(sorted([AGENT_NAME, chat_id]))
                zenoh_session.put(f"wc/dm/{pair}/messages", msg)

        return f"Sent to {chat_id}"
