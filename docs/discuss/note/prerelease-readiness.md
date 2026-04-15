# Pre-release 准备状态

> 更新于 2026-04-16

## 已完成（可直接进入 pre-release）

### 架构 + 功能开发

| 任务 | commit | tests |
|------|--------|-------|
| Phase 4.6.1 server.py 拆分 | b846b63 | test_architecture_split.py |
| Phase 4.6.2 IRC 消息协议 | 49bd728 | test_irc_message_protocol.py |
| Phase 4.6.3 routing 配置 | a5c3e30 | test_routing_config.py |
| Phase 4.6.4 /review + SLA | 718cfc1 | test_review_command.py + test_sla_alerts.py |
| Phase 4.6.5 card+thread | ff94e92 | feishu_bridge/tests/ |
| Phase 4.6.6 P2 commands | 4771f9a | test_p2_commands.py |
| Phase 4.6.7 SLA timer | 54af50e | test_sla_timers.py |
| Gate fix | 542fb29 | test_gate_enforcement.py |
| Card action (CSAT) | f5fc661 | test_card_action.py + test_csat_flow.py |
| DB consolidation | 9e95d62 | test_db_consolidation.py + test_db_lifecycle.py |

**总计**: 247 tests passed, 0 failed, 48 artifacts

### 文档

| 文档 | 状态 |
|------|------|
| spec/ 8 个文件 | ralph-loop 对齐完成 |
| plan/06 (Phase 4.6) | 完成 |
| plan/07 (Phase Final) | 架构前置全部 ✅ |
| plan/08 (DB consolidation) | 已完成已合并 |
| note/prerelease-todo.md | Issue 1 待合并, Issue 2 ✅ |

### 飞书平台

| 配置 | 状态 |
|------|------|
| App 机器人 | ✅ 已开 |
| 3 个测试群 | ✅ 已创建 |
| im:message / im:chat / im:resource 权限 | ✅ 已开 |
| im.message.receive_v1 事件 | ✅ 已订阅 |
| card.action.trigger 卡片回调 | ✅ 已订阅 (长连接) |

### 测试配置文件

| 文件 | 状态 |
|------|------|
| tests/pre_release/routing.toml | ✅ 已创建 |
| tests/pre_release/feishu-e2e-config.yaml | ✅ 模板已创建，chat_id 需替换 |

---

## 未完成（阻塞 pre-release 测试执行）

### P0: 测试基础设施开发

详见 eval-doc: `cs-eval-prerelease-infra`

| 缺失项 | 工作量 | 说明 |
|--------|--------|------|
| FeishuTestClient 7 个新方法 | ~100 行 | assert_message_edited, assert_card_appears, assert_card_updated, send_thread_reply, assert_thread_message_appears, send_message_as_operator, click_card_action |
| full_stack fixture | ~80 行 | 7 步启动链路 + teardown |
| test_feishu_e2e.py | ~150 行 | 9 类 17 个 test case（07-phase-final 有完整代码） |
| evidence/ 目录结构 | 少量 | mkdir + asciinema 录制脚本 |

**开发方式**: 新 session + dev-loop 闭环
**分支**: fix/prerelease-infra (从 refactor/channel-server 创建)

### P1: 服务启动验证

在写测试前需确认各服务可正常启动：
- [ ] ergo IRC server 可启动 (zchat irc daemon start)
- [ ] channel-server 独立进程可启动 (uv run zchat-channel)
- [ ] agent_mcp 可启动 (uv run zchat-agent-mcp)
- [ ] feishu_bridge 可启动 (uv run python -m feishu_bridge.bridge)
- [ ] zellij session 管理正常
- [ ] asciinema 录制正常

### P2: 飞书 chat_id 填入

feishu-e2e-config.yaml 中 3 个群的 chat_id 需要替换为真实值。

---

## 后续需要拆分的 pre-fix 项（不阻塞 pre-release）

### fix/language-dir (已有代码，待合并到 dev)

_ensure_ergo_languages() 3 级 fallback，不阻塞 channel-server。

### 3 个 E2E WebSocket flaky errors

tests/e2e 中 3 个测试偶发 WebSocket handshake 失败。
原因：bridge_ws fixture 中 websockets.connect 在 channel-server 进程未完全就绪时连接。
修复方向：增加 retry 或等待 Bridge API ready 信号。

### test_feishu_e2e.py 中 click_card_action 可行性

可能无法完全自动化飞书卡片点击。需评估方案 A（直接调用 _on_card_action）或 pytest.skip + 手动截图。
