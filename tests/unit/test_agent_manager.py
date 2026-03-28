import os
import json
import tempfile

from zchat.cli.agent_manager import AgentManager


def _make_manager(state_file="/tmp/test-agents.json", env_file="", claude_args=None):
    return AgentManager(
        irc_server="localhost", irc_port=6667, irc_tls=False,
        username="alice", default_channels=["#general"],
        env_file=env_file,
        claude_args=claude_args or ["--permission-mode", "bypassPermissions"],
        state_file=state_file,
    )


def test_scope_agent_name():
    mgr = _make_manager()
    assert mgr.scoped("helper") == "alice-helper"
    assert mgr.scoped("alice-helper") == "alice-helper"


def test_create_workspace_has_claude_settings():
    """Workspace should contain .claude/settings.local.json with MCP tool permissions."""
    mgr = _make_manager(state_file="/tmp/test-agents-ws2.json")
    ws = mgr._create_workspace("alice-helper", ["#general"])
    assert os.path.isdir(ws)
    assert not os.path.exists(os.path.join(ws, ".mcp.json"))
    settings_path = os.path.join(ws, ".claude", "settings.local.json")
    assert os.path.isfile(settings_path)
    with open(settings_path) as f:
        settings = json.load(f)
    assert "mcp__zchat-channel__reply" in settings["permissions"]["allow"]
    assert "mcp__zchat-channel__join_channel" in settings["permissions"]["allow"]
    import shutil
    shutil.rmtree(ws)


def test_agent_state_persistence(tmp_path):
    state_file = str(tmp_path / "agents.json")
    mgr = _make_manager(state_file=state_file)
    mgr._agents["alice-helper"] = {
        "workspace": "/tmp/x", "pane_id": "%42", "status": "running",
        "created_at": 0, "channels": ["#general"],
    }
    mgr._save_state()
    mgr2 = _make_manager(state_file=state_file)
    assert "alice-helper" in mgr2._agents
    assert mgr2._agents["alice-helper"]["pane_id"] == "%42"
