"""单元测试：zchat channel create/list + zchat agent join 命令。"""
from __future__ import annotations

import json
import os

import pytest
from typer.testing import CliRunner

from zchat.cli.app import app
from zchat.cli.project import (
    create_project_config,
    list_channels,
    add_channel,
    normalize_channel_name,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixture: 隔离 ZCHAT_HOME
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path, monkeypatch):
    """Create a temporary project and set it as default."""
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    create_project_config("testproj", server="local", nick="alice", channels="#general")
    # 写 default 文件，让 resolve_project() 自动选中
    (tmp_path / "default").write_text("testproj")
    return tmp_path


# ---------------------------------------------------------------------------
# normalize_channel_name 工具函数
# ---------------------------------------------------------------------------

def test_normalize_channel_name_with_hash():
    assert normalize_channel_name("#foo") == "#foo"


def test_normalize_channel_name_without_hash():
    assert normalize_channel_name("foo") == "#foo"


def test_normalize_channel_name_preserves_hash():
    assert normalize_channel_name("#customer-a") == "#customer-a"


# ---------------------------------------------------------------------------
# add_channel / list_channels 工具函数（直接调用，不走 CLI）
# ---------------------------------------------------------------------------

def test_add_channel_writes_config(project):
    add_channel("testproj", "#support", channel_type="customer", description="Customer support")
    channels = list_channels("testproj")
    assert "#support" in channels
    assert channels["#support"]["type"] == "customer"
    assert channels["#support"]["description"] == "Customer support"


def test_add_channel_duplicate_raises(project):
    add_channel("testproj", "#support")
    with pytest.raises(ValueError, match="already exists"):
        add_channel("testproj", "#support")


def test_add_channel_minimal(project):
    """type/description 均为空时也能正常写入。"""
    add_channel("testproj", "#minimal")
    channels = list_channels("testproj")
    assert "#minimal" in channels
    assert channels["#minimal"] == {}


# ---------------------------------------------------------------------------
# CLI: channel create
# ---------------------------------------------------------------------------

def test_channel_create_writes_config(project):
    result = runner.invoke(app, ["channel", "create", "#ops"])
    assert result.exit_code == 0, result.output
    channels = list_channels("testproj")
    assert "#ops" in channels


def test_channel_create_normalizes_hash_prefix(project):
    """传 'foo'（无 #）→ 存 '#foo'。"""
    result = runner.invoke(app, ["channel", "create", "foo"])
    assert result.exit_code == 0, result.output
    channels = list_channels("testproj")
    assert "#foo" in channels


def test_channel_create_with_type_and_description(project):
    result = runner.invoke(
        app,
        ["channel", "create", "#customer-a", "--type", "customer", "--description", "Customer A 支持群"],
    )
    assert result.exit_code == 0, result.output
    channels = list_channels("testproj")
    assert channels["#customer-a"]["type"] == "customer"
    assert channels["#customer-a"]["description"] == "Customer A 支持群"


def test_channel_create_duplicate_fails(project):
    runner.invoke(app, ["channel", "create", "#ops"])  # 第一次
    result = runner.invoke(app, ["channel", "create", "#ops"])  # 重复
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_channel_create_no_project_fails(tmp_path, monkeypatch):
    """没有 project 时应报错退出。"""
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    result = runner.invoke(app, ["channel", "create", "#ops"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI: channel list
# ---------------------------------------------------------------------------

def test_channel_list_empty(project):
    result = runner.invoke(app, ["channel", "list"])
    assert result.exit_code == 0
    assert "No channels" in result.output


def test_channel_list_formats(project):
    add_channel("testproj", "#alpha", channel_type="squad", description="Alpha team")
    add_channel("testproj", "#beta", channel_type="general")
    result = runner.invoke(app, ["channel", "list"])
    assert result.exit_code == 0
    assert "#alpha" in result.output
    assert "squad" in result.output
    assert "Alpha team" in result.output
    assert "#beta" in result.output


def test_channel_list_no_project_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    result = runner.invoke(app, ["channel", "list"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI: agent join
# ---------------------------------------------------------------------------

def _write_agent_state(projects_dir: str, state: dict):
    """Helper: write state.json to project state file path."""
    state_path = os.path.join(projects_dir, "testproj", "state.json")
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f)


def _read_agent_state(projects_dir: str) -> dict:
    state_path = os.path.join(projects_dir, "testproj", "state.json")
    with open(state_path) as f:
        return json.load(f)


@pytest.fixture()
def project_with_channel(project):
    """project fixture + 预注册 #support channel + 一个离线 agent。"""
    add_channel("testproj", "#support")
    state = {
        "agents": {
            "alice-helper": {
                "type": "claude",
                "status": "offline",
                "channels": ["#general"],
                "workspace": "/tmp/ws",
                "created_at": 0,
            }
        }
    }
    _write_agent_state(str(project / "projects"), state)
    return project


def test_agent_join_adds_channel_to_state(project_with_channel, monkeypatch):
    monkeypatch.setenv("ZCHAT_HOME", str(project_with_channel))
    monkeypatch.setattr("zchat.cli.auth.get_username", lambda: "alice")
    result = runner.invoke(app, ["agent", "join", "helper", "#support"])
    assert result.exit_code == 0, result.output
    state = _read_agent_state(str(project_with_channel / "projects"))
    channels = state["agents"]["alice-helper"]["channels"]
    assert "#support" in channels


def test_agent_join_dedupes(project_with_channel, monkeypatch):
    """重复 join 同一 channel 不应产生重复条目。"""
    monkeypatch.setenv("ZCHAT_HOME", str(project_with_channel))
    monkeypatch.setattr("zchat.cli.auth.get_username", lambda: "alice")
    runner.invoke(app, ["agent", "join", "helper", "#support"])
    runner.invoke(app, ["agent", "join", "helper", "#support"])
    state = _read_agent_state(str(project_with_channel / "projects"))
    channels = state["agents"]["alice-helper"]["channels"]
    assert channels.count("#support") == 1


def test_agent_join_rejects_unknown_channel(project_with_channel, monkeypatch):
    """channel 未注册时报错退出。"""
    monkeypatch.setenv("ZCHAT_HOME", str(project_with_channel))
    monkeypatch.setattr("zchat.cli.auth.get_username", lambda: "alice")
    result = runner.invoke(app, ["agent", "join", "helper", "#unknown"])
    assert result.exit_code != 0
    assert "not registered" in result.output


def test_agent_join_no_project_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("ZCHAT_HOME", str(tmp_path))
    result = runner.invoke(app, ["agent", "join", "helper", "#support"])
    assert result.exit_code != 0


def test_agent_join_unknown_agent_fails(project_with_channel, monkeypatch):
    """agent 不在 state 中时报错退出。"""
    monkeypatch.setenv("ZCHAT_HOME", str(project_with_channel))
    monkeypatch.setattr("zchat.cli.auth.get_username", lambda: "alice")
    result = runner.invoke(app, ["agent", "join", "nonexistent", "#support"])
    assert result.exit_code != 0


def test_agent_join_normalizes_channel_name(project_with_channel, monkeypatch):
    """传入不带 # 的 channel 名称应自动加 #。"""
    monkeypatch.setenv("ZCHAT_HOME", str(project_with_channel))
    monkeypatch.setattr("zchat.cli.auth.get_username", lambda: "alice")
    result = runner.invoke(app, ["agent", "join", "helper", "support"])  # 不带 #
    assert result.exit_code == 0, result.output
    state = _read_agent_state(str(project_with_channel / "projects"))
    channels = state["agents"]["alice-helper"]["channels"]
    assert "#support" in channels
