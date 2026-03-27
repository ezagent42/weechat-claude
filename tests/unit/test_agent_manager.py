import os
import json
import tempfile

from zchat.cli.agent_manager import AgentManager


def test_scope_agent_name():
    mgr = AgentManager(irc_server="localhost", irc_port=6667, irc_tls=False,
                       channel_server_dir="/tmp", username="alice",
                       default_channels=["#general"],
                       state_file="/tmp/test-agents-scope.json")
    assert mgr.scoped("helper") == "alice-helper"
    assert mgr.scoped("alice-helper") == "alice-helper"


def test_create_workspace():
    mgr = AgentManager(irc_server="localhost", irc_port=6667, irc_tls=False,
                       channel_server_dir="/tmp/fake", username="alice",
                       default_channels=["#general"],
                       state_file="/tmp/test-agents-ws.json")
    ws = mgr._create_workspace("alice-helper", ["#general"])
    assert os.path.isdir(ws)
    mcp_path = os.path.join(ws, ".mcp.json")
    assert os.path.isfile(mcp_path)
    with open(mcp_path) as f:
        mcp = json.load(f)
    env = mcp["mcpServers"]["weechat-channel"]["env"]
    assert env["AGENT_NAME"] == "alice-helper"
    assert env["IRC_SERVER"] == "localhost"
    assert env["IRC_PORT"] == "6667"
    assert env["IRC_CHANNELS"] == "general"
    assert env["IRC_TLS"] == "false"
    import shutil
    shutil.rmtree(ws)


def test_agent_state_persistence(tmp_path):
    state_file = str(tmp_path / "agents.json")
    mgr = AgentManager(irc_server="localhost", irc_port=6667, irc_tls=False,
                       channel_server_dir="/tmp", username="alice",
                       default_channels=["#general"], state_file=state_file)
    mgr._agents["alice-helper"] = {
        "workspace": "/tmp/x", "pane_id": "%42", "status": "running",
        "created_at": 0, "channels": ["#general"],
    }
    mgr._save_state()
    mgr2 = AgentManager(irc_server="localhost", irc_port=6667, irc_tls=False,
                        channel_server_dir="/tmp", username="alice",
                        default_channels=["#general"], state_file=state_file)
    assert "alice-helper" in mgr2._agents
    assert mgr2._agents["alice-helper"]["pane_id"] == "%42"
