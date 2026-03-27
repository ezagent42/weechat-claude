"""Shared test fixtures for zchat tests."""

import sys
import os
import pytest

# Add weechat-channel-server to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", "weechat-channel-server"))


@pytest.fixture
def agent_name():
    """Default agent name for tests (scoped to creator per issue #2)."""
    return "alice-agent0"
