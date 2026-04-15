# Phase 4.6 — 架构拆分 + 新功能

> Phase 4 (feat/server-v1) 完成后、Phase Final 之前的开发任务
> 基于 `docs/discuss/note/prerelease-todo.md` 中的架构决策
> 每个 Task 对应一个 dev-loop 闭环

---

## 依赖关系

```
Phase 4 (feat/server-v1) ── 138 tests PASS
    │
    └── Phase 4.5 (feat/feishu-bridge) ── 消息解析 + 群映射
            │
            └── Phase 4.6 (本文档) ── 架构拆分 + 新功能
                    │
                    ├── Task 4.6.1: server.py 拆分（无依赖）
                    ├── Task 4.6.2: IRC 消息协议（依赖 4.6.1）
                    ├── Task 4.6.3: routing 配置（依赖 4.6.1）
                    ├── Task 4.6.4: /review + SLA breach（依赖 4.6.1 + 4.6.3）
                    └── Task 4.6.5: feishu card+thread（依赖 4.6.2）
                            │
                            └── Phase Final (飞书全自动 E2E)
```

**分支**: `feat/architecture-split`（从 `feat/server-v1` 最新 merge 创建）

---

## Task 4.6.1: server.py 拆分

> server.py (644行) → 独立进程 server.py (~300行) + 轻量 agent_mcp.py (~200行)

### Spec 参考

- `docs/discuss/note/prerelease-todo.md` — 决策 #1 (channel-server 独立化)
- `docs/discuss/spec/channel-server/02-channel-server.md` — §1 模块职责

### Dev-loop 闭环

#### 1. eval-doc

**预期行为**:
- `server.py` 改造为独立进程：IRC bot (cs-bot) + Bridge API :9999 + engine 组装
- `server.py` 不再包含 MCP Server 相关代码（`create_server`/`register_tools`/`@server.list_tools`）
- `agent_mcp.py` 新建：MCP stdio + tools(reply/join/send_side_message) + IRC 连接 + @mention 注入
- `pyproject.toml` 新增 entry_point: `zchat-agent-mcp = "agent_mcp:entry_point"`
- 原有 138 unit/E2E tests 全部 PASS（engine/ + protocol/ + bridge_api/ 0 改动）
- E2E conftest.py 的 `channel_server` fixture 改为 `subprocess.Popen(["uv", "run", "zchat-channel"])`

#### 2. test-plan

| # | 测试名 | 类型 | 验证点 |
|---|--------|------|--------|
| 1 | test_server_starts_as_standalone | E2E | server.py 作为独立进程启动，IRC bot 连接成功，Bridge API :9999 可达 |
| 2 | test_agent_mcp_starts | E2E | agent_mcp.py 通过 MCP stdio 启动，list_tools 返回 reply/join/send_side_message |
| 3 | test_agent_mcp_reply_sends_irc | E2E | agent_mcp reply() → IRC PRIVMSG 发出到 #conv-{id} |
| 4 | test_agent_mcp_mention_injection | E2E | IRC @mention → agent_mcp MCP notification 注入 |
| 5 | test_existing_138_tests_pass | regression | 原有 138 tests 全部 PASS |
| 6 | test_entry_points | unit | `zchat-channel` 和 `zchat-agent-mcp` 两个 entry_point 均可解析 |

#### 3. test-code

在 `tests/e2e/test_architecture_split.py` 中实现上述 E2E tests。fixture 改造:

```python
@pytest.fixture
def channel_server(ergo_server):
    """启动 channel-server 独立进程（非 MCP stdio）"""
    proc = subprocess.Popen(
        ["uv", "run", "zchat-channel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # 等待 IRC 连接 + Bridge API ready
    _wait_for_bridge_api(port=9999, timeout=10)
    yield proc
    proc.terminate()
    proc.wait()
```

#### 4. implement

**步骤**:
1. 从 `server.py` 提取 MCP 相关代码到 `agent_mcp.py`
2. `server.py` 去掉 MCP 依赖，改为独立进程入口（IRC bot + Bridge API + engine）
3. `agent_mcp.py` 实现 MCP stdio + 3 个 tools + IRC 连接 + @mention 注入
4. `pyproject.toml` 新增 `zchat-agent-mcp` entry_point
5. E2E conftest.py fixture 适配

**关键约束**:
- engine/ protocol/ bridge_api/ transport/ **0 改动**
- 只改 server.py + 新建 agent_mcp.py + 改 conftest.py
- 原有 138 tests 必须继续 PASS

#### 5. test-run

```bash
# 回归
uv run pytest tests/unit/ -v
uv run pytest tests/e2e/ -v -m e2e

# 新增
uv run pytest tests/e2e/test_architecture_split.py -v
```

---

## Task 4.6.2: IRC 消息协议

> agent_mcp 通过 IRC 消息前缀与 channel-server 通信

### Spec 参考

- `docs/discuss/note/prerelease-todo.md` — 决策 #1 (IRC 消息格式约定)
- `docs/discuss/spec/channel-server/02-channel-server.md` — §4 Agent MCP Tools

### Dev-loop 闭环

#### 1. eval-doc

**预期行为**:
- `agent_mcp.reply()` 生成 UUID message_id 并返回给 Claude Code
- `reply(edit_of=msg_id)` → IRC PRIVMSG 用 `__edit:msg_id:text` 前缀
- `reply(side=True)` → IRC PRIVMSG 用 `__side:text` 前缀
- `channel-server` IRC bot 解析 `__edit:` / `__side:` 前缀 → 路由到 Bridge API
- 无前缀的普通消息，visibility 由 Gate 判定

#### 2. test-plan

| # | 测试名 | 类型 | 验证点 |
|---|--------|------|--------|
| 1 | test_reply_returns_message_id | unit | reply() 返回非空 UUID |
| 2 | test_reply_edit_irc_prefix | unit | reply(edit_of="msg_001") 生成 `__edit:msg_001:text` |
| 3 | test_reply_side_irc_prefix | unit | reply(side=True) 生成 `__side:text` |
| 4 | test_cs_parse_edit_prefix | unit | channel-server 解析 `__edit:msg_001:text` → type=edit, msg_id=msg_001 |
| 5 | test_cs_parse_side_prefix | unit | channel-server 解析 `__side:text` → type=reply, visibility=side |
| 6 | test_cs_parse_no_prefix | unit | channel-server 解析普通消息 → Gate 判定 |
| 7 | test_edit_e2e_flow | E2E | agent_mcp reply(edit_of) → IRC → channel-server → Bridge API `{type: "edit"}` |
| 8 | test_side_e2e_flow | E2E | agent_mcp reply(side=True) → IRC → channel-server → Bridge API `{visibility: "side"}` |

#### 3. test-code

- unit tests: `tests/unit/test_irc_message_protocol.py`
- E2E tests: `tests/e2e/test_message_protocol.py`

#### 4. implement

**步骤**:
1. `agent_mcp.py`: reply() 生成 UUID，按参数组装 IRC 前缀
2. `server.py` (或 `transport/irc_transport.py`): 新增 `parse_irc_prefix()` 函数
3. `server.py`: on_pubmsg 中调用 `parse_irc_prefix()`，按类型路由到 Bridge API

#### 5. test-run

```bash
uv run pytest tests/unit/test_irc_message_protocol.py -v
uv run pytest tests/e2e/test_message_protocol.py -v
```

---

## Task 4.6.3: Routing 配置

> channel-server 启动时加载 routing.toml，执行 auto-dispatch 和 escalation

### Spec 参考

- `docs/discuss/spec/channel-server/10-routing-config.md` — 完整规范
- `docs/discuss/note/prerelease-todo.md` — 决策 #6 (Agent 编排)

### Dev-loop 闭环

#### 1. eval-doc

**预期行为**:
- channel-server 启动时加载 `routing.toml`（路径通过环境变量或 config.toml 指定）
- 新 conversation 创建时自动 dispatch `default_agents`
- 收到 escalation event 时按 `escalation_chain` 顺序 dispatch
- `/dispatch` 命令验证 agent 在 `available_agents` 白名单中
- routing.toml 不存在时使用空默认值（不报错）

#### 2. test-plan

| # | 测试名 | 类型 | 验证点 |
|---|--------|------|--------|
| 1 | test_load_routing_config | unit | 正确解析 routing.toml |
| 2 | test_load_missing_config | unit | 文件不存在时返回默认空配置 |
| 3 | test_auto_dispatch_on_create | E2E | conversation.created → default_agents 自动 JOIN |
| 4 | test_auto_dispatch_agent_offline | E2E | agent 不在线时跳过，不阻塞 |
| 5 | test_escalation_chain | E2E | escalation event → 按顺序 dispatch 到第一个可用 agent |
| 6 | test_escalation_to_operator | E2E | escalation_chain 中 "operator" → Bridge API 发告警 |
| 7 | test_dispatch_whitelist_pass | unit | agent 在白名单中 → 允许 dispatch |
| 8 | test_dispatch_whitelist_reject | unit | agent 不在白名单中 → 拒绝并返回错误 |
| 9 | test_dispatch_empty_whitelist | unit | 白名单为空 → 不限制 |

#### 3. test-code

- unit tests: `tests/unit/test_routing_config.py`
- E2E tests: `tests/e2e/test_routing.py`

#### 4. implement

**步骤**:
1. 新建 `routing_config.py`: `load_routing_config()` + `RoutingConfig` dataclass
2. `server.py` main() 中加载 routing 配置
3. EventBus 订阅 `conversation.created` → `_on_conversation_created()` 执行 auto-dispatch
4. 新增 `__escalation:` IRC 前缀解析 → EventBus escalation event
5. `/dispatch` handler 增加白名单验证

#### 5. test-run

```bash
uv run pytest tests/unit/test_routing_config.py -v
uv run pytest tests/e2e/test_routing.py -v
```

---

## Task 4.6.4: /review + SLA breach 告警

> /review 命令 + SLA timer breach 时向 admin群 发告警

### Spec 参考

- `docs/discuss/spec/channel-server/04-prd-mapping.md` — US-3.2 (/review) + US-3.3 (SLA)
- `docs/discuss/note/prerelease-todo.md` — PRD 覆盖汇总表

### Dev-loop 闭环

#### 1. eval-doc

**预期行为**:
- `/review` 是 channel-server 内建命令（不是 agent 行为）
- `/review` handler: EventBus.query 聚合昨日统计（对话数、接管次数、结案率、CSAT 均分）  <!-- 平均首回时间 deferred to v1.1，需 sla_first_reply timer 基础设施 -->
- SLA timer breach → Bridge API 通知 admin群（单次 breach 告警，v1.0 不做滚动平均）
- 告警消息包含 conversation_id + breach 类型 + 超时时长

#### 2. test-plan

| # | 测试名 | 类型 | 验证点 |
|---|--------|------|--------|
| 1 | test_review_command_parse | unit | `/review` 被 CommandParser 正确解析 |
| 2 | test_review_returns_stats | unit | EventBus.query 聚合返回格式化统计文本 |
| 3 | test_review_empty_data | unit | 无数据时返回 "暂无统计数据" |
| 4 | test_sla_breach_alert | E2E | sla_first_reply timer 超时 → Bridge API 收到告警 event |
| 5 | test_sla_breach_message_format | unit | 告警消息包含 conv_id + breach 类型 + 超时时长 |
| 6 | test_sla_onboard_breach_alert | E2E | sla_onboard(3s) 超时 → Bridge API admin 告警 |

#### 3. test-code

- unit tests: `tests/unit/test_review_command.py`
- E2E tests: `tests/e2e/test_sla_alerts.py`

#### 4. implement

**步骤**:
1. `protocol/commands.py`: **新增** `/review` 命令定义（当前 `_COMMAND_DEFS` 无 review，需添加 `"review": []`）
2. `server.py` `_on_admin_command()`: 实现 /review handler
   - `event_bus.query(since=yesterday)` → 聚合统计
   - 格式化输出: 对话数 / 接管次数 / 结案率(%) / CSAT均分
3. `engine/timer_manager.py`: timer breach callback 中发布 `sla.breach` event
4. EventBus 订阅 `sla.breach` → Bridge API 发 admin 告警
5. 告警消息格式: `[SLA 告警] conv_id={id} breach={type} timeout={duration}s`

#### 5. test-run

```bash
uv run pytest tests/unit/test_review_command.py -v
uv run pytest tests/e2e/test_sla_alerts.py -v
```

---

## Task 4.6.5: feishu_bridge card+thread 模型

> squad群 card+thread 聚合 + operator-in-customer-chat 自动 hijack

### Spec 参考

- `docs/discuss/spec/channel-server/09-feishu-bridge.md` — §6 Visibility 路由
- `docs/discuss/note/prerelease-todo.md` — 决策 #3 (Squad群 thread 模型) + 决策 #4 (Takeover 触发)

### Dev-loop 闭环

#### 1. eval-doc

**预期行为**:
- `conversation.created` → feishu_bridge 在 squad群 发 interactive card（thread root）
- public reply → 双写（customer_chat + squad thread）
- side message → squad thread only
- `mode.changed` → update_card 刷新状态
- `conversation.closed` → update_card 标记关闭
- cs→feishu 消息 ID 映射: `{cs_msg_id: feishu_msg_id}`，edit 时查映射调 `update_message()`
- operator 在 customer_chat 发消息 → GroupManager 检测 → 自动发 operator_join + operator_command(/hijack)

#### 2. test-plan

| # | 测试名 | 类型 | 验证点 |
|---|--------|------|--------|
| 1 | test_conv_created_sends_card | unit | conversation.created → send_card() 调用 |
| 2 | test_card_is_thread_root | unit | card_msg_id 存入 ConvThread |
| 3 | test_public_reply_dual_write | unit | visibility=public → send_text(customer) + reply_in_thread(squad) |
| 4 | test_side_thread_only | unit | visibility=side → reply_in_thread(squad) only |
| 5 | test_mode_changed_updates_card | unit | mode.changed → update_message(card_msg_id) |
| 6 | test_conv_closed_updates_card | unit | conversation.closed → update_card 标记关闭 |
| 7 | test_msg_id_mapping_for_edit | unit | reply 存 {cs_msg_id: feishu_msg_id}，edit 查映射 |
| 8 | test_operator_in_customer_chat | unit | known_operator 在 customer_chat 发消息 → is_operator_in_customer_chat() 返回 True |
| 9 | test_auto_hijack_flow | E2E | operator 在 customer_chat 发消息 → Bridge API 收到 operator_join + operator_command(/hijack) |
| 10 | test_card_thread_e2e | E2E (需飞书凭证) | 完整流程: 新客户 → 卡片 → 回复 → thread → edit → 关闭 |

#### 3. test-code

- unit tests: `feishu_bridge/tests/test_visibility_router.py` (扩展)
- unit tests: `feishu_bridge/tests/test_group_manager.py` (扩展)
- E2E tests: `tests/e2e/test_feishu_card_thread.py`

#### 4. implement

**步骤**:
1. `feishu_bridge/visibility_router.py`: 重构为 card+thread 模型
   - 新增 `ConvThread` dataclass
   - `on_conversation_created()`: send_card → 存 card_msg_id
   - `route()`: 按 visibility 双写或 thread only
   - `on_mode_changed()`: update_card
   - `on_conversation_closed()`: update_card 关闭标记
2. `feishu_bridge/sender.py`: 新增 `reply_in_thread(root_msg_id, text)` 方法
3. `feishu_bridge/visibility_router.py`: msg_id_map 存储 cs→feishu 映射
4. `feishu_bridge/group_manager.py`: 新增 `is_operator_in_customer_chat()`
5. `feishu_bridge/bridge.py`: `_on_message` 中检测 auto-hijack → 发 operator_join + operator_command

#### 5. test-run

```bash
# unit tests（无需飞书凭证）
cd feishu_bridge && uv run pytest tests/ -v

# E2E（需要飞书凭证 + channel-server 运行）
uv run pytest tests/e2e/test_feishu_card_thread.py -v
```

---

## Dev-loop 第 6 步: Artifact Registry

每个 Task 完成后，注册 artifact（`cs-` 前缀）：

```bash
# Task 4.6.1
/dev-loop-skills:skill-6-artifact-registry register --type eval-doc --id cs-eval-architecture-split
/dev-loop-skills:skill-6-artifact-registry register --type test-plan --id cs-plan-architecture-split
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-architecture-split
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-architecture-split

# Task 4.6.2
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-irc-protocol
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-irc-protocol

# Task 4.6.3
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-routing
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-routing

# Task 4.6.4
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-review-sla
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-review-sla

# Task 4.6.5
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-card-thread
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-card-thread
```

闭环完成标志: 每个 Task 的 `cs-report-*` 存在，0 FAIL 0 SKIP。

---

## 补充 Task: P2 命令 + SLA Timer 自动触发

以下功能在 06-gap-fixes.md 中定义但无 dev-loop task。不阻塞 Phase Final，可在 Phase Final 后补充：

### Task 4.6.6: P2 命令 handler（/abandon /assign /reassign /squad）

```
eval-doc: cs-eval-p2-commands
test-plan: cs-plan-p2-commands
底层方法全部 WORKING（SquadRegistry.assign/reassign/unassign, ConversationManager.close）
只需在 wire_bridge_callbacks() 中接线，模式同 /hijack handler
预估: 1-2h
```

### Task 4.6.7: SLA Timer 自动触发

```
eval-doc: cs-eval-sla-timers
test-plan: cs-plan-sla-timers
spec 参考: 06-gap-fixes.md 修复 1
实现: App plugin 在 conversation.created 时设置 sla_onboard timer，
      在 reply 时设置 sla_placeholder/sla_slow_query timer
      TimerManager WORKING，只需 plugin hook 接入
预估: 2-3h
```

---

## 验收标准

### 全部 Task 完成后

```bash
# 1. 原有 138 tests 全部 PASS（0 回归）
uv run pytest tests/unit/ tests/e2e/ -v

# 2. 新增 tests 全部 PASS
uv run pytest tests/unit/test_irc_message_protocol.py tests/unit/test_routing_config.py tests/unit/test_review_command.py -v
uv run pytest tests/e2e/test_architecture_split.py tests/e2e/test_message_protocol.py tests/e2e/test_routing.py tests/e2e/test_sla_alerts.py -v

# 3. entry_points 可用
uv run zchat-channel --help     # 独立进程
uv run zchat-agent-mcp --help   # 轻量 MCP

# 4. 启动验证
# ergo + zchat-channel + agent_mcp + feishu_bridge 全部正常启动
# fast-agent + deep-agent 在 IRC 可见
# Bridge API ws://localhost:9999 可达
# feishu_bridge 注册成功
```

### Merge 条件

- 所有 tests PASS
- `git diff --stat feat/server-v1..feat/architecture-split` 确认改动范围
- engine/ protocol/ bridge_api/ 目录 0 改动（确认隔离性）
- PR review

---


*Phase 4.6 计划 · 基于 prerelease-todo.md 架构决策 · 2026-04-15*
