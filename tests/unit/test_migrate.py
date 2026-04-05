"""Tests for config and state migration."""
from __future__ import annotations

import json


def test_migrate_config_tmux_to_zellij(tmp_path):
    """Old config with [tmux] section should be migrated to new format."""
    project_dir = tmp_path / "local"
    project_dir.mkdir()
    config_path = project_dir / "config.toml"
    config_path.write_text("""
[irc]
server = "127.0.0.1"
port = 6667
tls = false

[agents]
default_type = "claude"
default_channels = ["#general"]
username = "alice"

[tmux]
session = "zchat-abc12345-local"
""")
    from zchat.cli.migrate import migrate_config_if_needed
    result = migrate_config_if_needed(str(project_dir))
    assert result is True

    import tomllib
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    assert "zellij" in cfg
    assert cfg["zellij"]["session"] == "zchat-local"
    assert "tmux" not in cfg
    assert "irc" not in cfg
    assert cfg["server"] == "127.0.0.1"
    assert cfg["default_runner"] == "claude"
    assert (project_dir / "config.toml.bak").exists()


def test_migrate_config_already_new_format(tmp_path):
    """New format config should not be migrated."""
    config_path = tmp_path / "config.toml"
    config_path.write_text("""
server = "local"
default_runner = "claude-channel"
default_channels = ["#general"]

[zellij]
session = "zchat-local"
""")
    from zchat.cli.migrate import migrate_config_if_needed
    result = migrate_config_if_needed(str(tmp_path))
    assert result is False


def test_migrate_state_json(tmp_path):
    """State with window_name and pane_id should be migrated."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "agents": {
            "alice-agent0": {
                "window_name": "alice-agent0",
                "pane_id": "%5",
                "status": "running",
            }
        },
        "irc": {
            "weechat_window": "weechat",
            "weechat_pane_id": "%1",
        }
    }))
    from zchat.cli.migrate import migrate_state_if_needed
    result = migrate_state_if_needed(str(tmp_path))
    assert result is True

    data = json.loads(state_path.read_text())
    agent = data["agents"]["alice-agent0"]
    assert "tab_name" in agent
    assert "window_name" not in agent
    assert "pane_id" not in agent
    assert agent["tab_name"] == "alice-agent0"

    irc = data["irc"]
    assert "weechat_tab" in irc
    assert "weechat_window" not in irc
    assert "weechat_pane_id" not in irc

    assert (tmp_path / "state.json.bak").exists()


def test_migrate_state_already_new(tmp_path):
    """State already in new format should not be modified."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "agents": {
            "alice-agent0": {"tab_name": "alice-agent0", "status": "running"}
        }
    }))
    from zchat.cli.migrate import migrate_state_if_needed
    result = migrate_state_if_needed(str(tmp_path))
    assert result is False
