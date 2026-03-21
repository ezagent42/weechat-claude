"""Tests for weechat-channel-server/tools.py"""

import json
import os
import pytest
from unittest.mock import MagicMock, AsyncMock

# Patch AGENT_NAME before importing tools
os.environ["AGENT_NAME"] = "agent0"

from tools import register_tools


class TestReplyTool:
    @pytest.fixture
    def mcp_and_session(self, mock_zenoh_session):
        mcp = MagicMock()
        # Capture the tool function when @mcp.tool() is called
        registered = {}
        def fake_tool():
            def decorator(func):
                registered[func.__name__] = func
                return func
            return decorator
        mcp.tool = fake_tool
        register_tools(mcp, mock_zenoh_session)
        return registered, mock_zenoh_session

    @pytest.mark.asyncio
    async def test_reply_to_private(self, mcp_and_session):
        tools, session = mcp_and_session
        result = await tools["reply"]("alice", "hello")
        assert "Sent" in result
        assert len(session.published) == 1
        key, payload = session.published[0]
        assert key == "wc/private/agent0_alice/messages"
        msg = json.loads(payload)
        assert msg["nick"] == "agent0"
        assert msg["body"] == "hello"
        assert msg["type"] == "msg"

    @pytest.mark.asyncio
    async def test_reply_to_channel(self, mcp_and_session):
        tools, session = mcp_and_session
        result = await tools["reply"]("#general", "hi channel")
        assert "Sent" in result
        key, payload = session.published[0]
        assert key == "wc/channels/general/messages"
        msg = json.loads(payload)
        assert msg["body"] == "hi channel"

    @pytest.mark.asyncio
    async def test_reply_message_format(self, mcp_and_session):
        tools, session = mcp_and_session
        await tools["reply"]("bob", "test")
        _, payload = session.published[0]
        msg = json.loads(payload)
        # Verify all required fields
        assert "id" in msg
        assert "nick" in msg
        assert "type" in msg
        assert "body" in msg
        assert "ts" in msg
        assert isinstance(msg["ts"], float)
