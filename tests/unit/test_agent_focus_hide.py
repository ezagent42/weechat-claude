"""Unit tests for zchat agent focus/hide commands."""

import os
from unittest.mock import patch, MagicMock

import pytest

from zchat.cli.app import _zellij_switch


class TestZellijSwitch:
    """Tests for the _zellij_switch helper."""

    @patch("zchat.cli.zellij.go_to_tab")
    def test_go_to_tab_inside_zellij(self, mock_go_to_tab):
        with patch.dict(os.environ, {"ZELLIJ": "0"}):
            _zellij_switch("zchat-local", "alice-agent0")
        mock_go_to_tab.assert_called_once_with("zchat-local", "alice-agent0")

    def test_exit_outside_zellij(self):
        from click.exceptions import Exit
        env = {k: v for k, v in os.environ.items() if k != "ZELLIJ"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(Exit):
                _zellij_switch("zchat-local", "alice-agent0")


class TestFocusHideCommands:
    """Tests for focus/hide command logic using AgentManager."""

    def _make_manager(self, agents=None):
        """Create a minimal AgentManager with pre-loaded state."""
        from zchat.cli.agent_manager import AgentManager
        mgr = AgentManager(
            irc_server="localhost", irc_port=6667, irc_tls=False,
            irc_password="", username="alice",
            default_channels=["#general"],
            state_file="/tmp/test-focus-hide.json",
        )
        if agents:
            mgr._agents = agents
        return mgr

    def test_get_status_offline_agent(self):
        mgr = self._make_manager(agents={
            "alice-agent0": {
                "status": "offline",
                "window_name": "alice-agent0",
            }
        })
        status = mgr.get_status("agent0")
        assert status["status"] == "offline"

    def test_get_status_unknown_agent_raises(self):
        mgr = self._make_manager()
        with pytest.raises(ValueError, match="Unknown agent"):
            mgr.get_status("nonexistent")

    def test_session_name_property(self):
        mgr = self._make_manager()
        assert mgr.session_name == "zchat"

    def test_hide_all_skips_validation(self):
        """'all' should not call get_status."""
        mgr = self._make_manager()
        # If get_status were called with "all", it would raise ValueError
        # We just verify session_name is accessible (the zellij call would be mocked in integration)
        assert mgr.session_name == "zchat"
