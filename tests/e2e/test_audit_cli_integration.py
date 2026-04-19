"""E2E: audit CLI 读 CS 产生的 audit.json。

场景：
  1. 用 AuditPlugin 写入 audit.json
  2. 用 zchat audit CLI 读出来，验证数据准确
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner


# 需要能 import plugins.audit.plugin 才能测试
# 添加 channel-server src 到 sys.path
_CS_SRC = Path(__file__).parent.parent.parent / "zchat-channel-server" / "src"
if str(_CS_SRC) not in sys.path:
    sys.path.insert(0, str(_CS_SRC))


@pytest.fixture
def cs_audit_json(tmp_path, monkeypatch):
    """模拟 CS 产生 audit.json。"""
    try:
        from plugins.audit.plugin import AuditPlugin
    except ModuleNotFoundError:
        pytest.skip("channel-server plugins 不可 import（e2e 需要 channel-server 源码）")

    path = tmp_path / "audit.json"
    audit = AuditPlugin(persist_path=path)

    async def run():
        # 模拟一个完整的生命周期
        await audit.on_ws_message({"channel": "conv-e2e", "source": "customer", "content": "hi"})
        await audit.on_ws_message({"channel": "conv-e2e", "source": "alice-fast-001", "content": "hello"})
        await audit.on_ws_event({
            "event": "mode_changed",
            "channel": "conv-e2e",
            "data": {"to": "takeover", "triggered_by": "op"},
        })
        await audit.on_ws_event({
            "event": "mode_changed",
            "channel": "conv-e2e",
            "data": {"to": "copilot", "triggered_by": "op"},
        })
        await audit.on_ws_event({"event": "channel_resolved", "channel": "conv-e2e", "data": {}})
        audit.record_csat("conv-e2e", 5)

    asyncio.run(run())

    monkeypatch.setenv("CS_DATA_DIR", str(tmp_path))
    return path


def test_cli_reads_cs_audit_json(cs_audit_json):
    """CLI 读取 CS 写的 audit.json，数据完整。"""
    from zchat.cli.app import app
    runner = CliRunner()

    result = runner.invoke(app, ["audit", "status", "--channel", "conv-e2e", "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["state"] == "resolved"
    assert data["message_count"] == 2
    assert len(data["takeovers"]) == 1
    assert data["csat_score"] == 5


def test_cli_report_aggregates(cs_audit_json):
    from zchat.cli.app import app
    runner = CliRunner()

    result = runner.invoke(app, ["audit", "report", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    # 有 1 个 takeover，1 个 resolved
    assert data["total_takeovers"] == 1
    assert data["total_resolved"] == 1
    # takeover → resolve 配对 100%
    assert data["escalation_resolve_rate"] == 1.0
    assert data["csat_mean"] == 5.0
