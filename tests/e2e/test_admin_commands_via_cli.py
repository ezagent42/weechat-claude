"""E2E: admin-agent 命令经 run_zchat_cli 路径正确映射。

admin-agent 的 soul.md 规定：
  /status → zchat audit status
  /review → zchat audit report
  /dispatch <type> <ch> → zchat agent create ... --type ... --channel ...

本测试不真实拉起 admin-agent，而是验证 CLI 端对应命令的响应和格式：
  - zchat audit status --json 能跑
  - zchat audit report --json 能跑
  - zchat agent create --type admin-agent 参数接受（至少 help / 参数解析不报错）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

_CS_SRC = Path(__file__).parent.parent.parent / "zchat-channel-server" / "src"
if str(_CS_SRC) not in sys.path:
    sys.path.insert(0, str(_CS_SRC))


runner = CliRunner()


@pytest.fixture
def populated_audit(tmp_path, monkeypatch):
    """构造一个带数据的 audit.json。"""
    try:
        from plugins.audit.plugin import AuditPlugin
    except ModuleNotFoundError:
        pytest.skip("channel-server 不可 import")

    import asyncio
    path = tmp_path / "audit.json"
    a = AuditPlugin(persist_path=path)

    async def _populate():
        await a.on_ws_message({"channel": "conv-1", "source": "customer", "content": "hi"})
        await a.on_ws_message({"channel": "conv-1", "source": "alice-fast-001", "content": "hello"})
        await a.on_ws_event({"event": "mode_changed", "channel": "conv-1", "data": {"to": "takeover"}})
        await a.on_ws_event({"event": "mode_changed", "channel": "conv-1", "data": {"to": "copilot"}})
        await a.on_ws_event({"event": "channel_resolved", "channel": "conv-1", "data": {}})
        a.record_csat("conv-1", 5)
        # 第二个 channel 活跃中
        await a.on_ws_message({"channel": "conv-2", "source": "customer", "content": "在吗"})

    asyncio.run(_populate())

    monkeypatch.setenv("CS_DATA_DIR", str(tmp_path))
    return path


def test_status_command_mapping(populated_audit):
    """admin-agent 处理 /status → run_zchat_cli(['audit', 'status'])。"""
    from zchat.cli.app import app
    result = runner.invoke(app, ["audit", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "channels" in data
    assert "aggregates" in data
    assert "conv-1" in data["channels"]
    assert "conv-2" in data["channels"]


def test_review_command_mapping(populated_audit):
    """admin-agent 处理 /review → run_zchat_cli(['audit', 'report'])。"""
    from zchat.cli.app import app
    result = runner.invoke(app, ["audit", "report", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # 应有完整聚合数据
    assert data["total_takeovers"] == 1
    assert data["total_resolved"] == 1
    assert data["escalation_resolve_rate"] == 1.0
    assert data["csat_mean"] == 5.0


def test_dispatch_command_args_parse(populated_audit):
    """/dispatch fast-agent conv-xxx → zchat agent create ... --type fast-agent --channel conv-xxx
    不真正启动 agent（需要 ergo），但验证参数被 CLI 接受。
    """
    from zchat.cli.app import app
    # 只测参数接受 —— 用 --help 避免真实创建 agent
    result = runner.invoke(app, ["agent", "create", "--help"])
    assert result.exit_code == 0
    # 确认 --type 和 --channel 参数存在
    assert "--type" in result.output
    assert "--channel" in result.output


def test_channel_list_command(populated_audit, tmp_path, monkeypatch):
    """admin 可能调用 zchat channel list。不需要 populated audit。"""
    from zchat.cli.app import app
    result = runner.invoke(app, ["channel", "--help"])
    assert result.exit_code == 0
    # 包含 create, list, remove, set-entry 子命令
    assert "create" in result.output
    assert "list" in result.output
    assert "remove" in result.output
    assert "set-entry" in result.output


def test_soul_md_only_references_existing_tools():
    """验证 4 个 agent 模板的 soul.md 只引用 reply / join_channel / run_zchat_cli。"""
    import re

    templates_dir = Path(__file__).parent.parent.parent / "zchat" / "cli" / "templates"
    if not templates_dir.exists():
        pytest.skip("templates dir not found")

    # 已被删除的 tool（任何 soul.md 不能引用）
    bad_tools = [
        "send_side_message",
        "query_status()",
        "query_review()",
        "query_squad()",
        "assign_agent()",
        "reassign_agent()",
    ]

    for soul in templates_dir.glob("*-agent/soul.md"):
        content = soul.read_text()
        for bad in bad_tools:
            assert bad not in content, f"{soul}: still references deleted tool {bad}"


def test_all_start_sh_whitelist_existing_tools():
    """所有 start.sh 的 settings.local.json 白名单只包含存在的 MCP tool。"""
    templates_dir = Path(__file__).parent.parent.parent / "zchat" / "cli" / "templates"
    for start_sh in templates_dir.glob("*/start.sh"):
        content = start_sh.read_text()
        # 不能有 send_side_message 白名单
        assert "mcp__zchat-agent-mcp__send_side_message" not in content, \
            f"{start_sh}: whitelist references deleted send_side_message"
        # 应该白名单了 reply + join_channel + run_zchat_cli
        if "mcp__zchat-agent-mcp" in content:
            assert "mcp__zchat-agent-mcp__reply" in content
            assert "mcp__zchat-agent-mcp__join_channel" in content
            assert "mcp__zchat-agent-mcp__run_zchat_cli" in content
