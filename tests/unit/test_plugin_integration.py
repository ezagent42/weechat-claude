"""Tests for plugin ↔ CLI integration: config.kdl generation, commands JSON."""
import json
import os

from zchat.cli.app import _write_config_kdl, _get_commands_json


def test_get_commands_json_returns_valid_json():
    """commands JSON should contain all non-hidden CLI commands."""
    raw = _get_commands_json()
    commands = json.loads(raw)
    names = [c["name"] for c in commands]
    assert "agent create" in names
    assert "shutdown" in names
    assert "list-commands" not in names  # hidden


def test_get_commands_json_includes_sources():
    """Commands with arg sources should include them."""
    commands = json.loads(_get_commands_json())
    agent_stop = next(c for c in commands if c["name"] == "agent stop")
    name_arg = next(a for a in agent_stop["args"] if a["name"] == "name")
    assert name_arg["source"] == "running_agents"


def test_write_config_kdl_contains_zchat_bin(tmp_path, monkeypatch):
    """config.kdl should pass zchat_bin to the palette plugin."""
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    path = _write_config_kdl(str(tmp_path))
    content = open(path).read()
    assert "zchat_bin" in content


def test_write_config_kdl_embeds_commands_json(tmp_path, monkeypatch):
    """config.kdl should embed commands JSON inline for WASM sandbox compat."""
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    path = _write_config_kdl(str(tmp_path))
    content = open(path).read()
    assert "commands_json" in content
    # The embedded JSON should contain known commands (escaped)
    assert "agent create" in content
    assert "shutdown" in content
