# Phase 4.6 执行 Prompt

> 复制以下 prompt 到新 session 中执行。
> 按 Task 顺序执行（4.6.1 → 4.6.2 → 4.6.3 → 4.6.4 → 4.6.5）。
> 每个 Task 是一个独立的 dev-loop 闭环。

---

## Prompt

```
你被启动在 zchat 项目根目录 (`~/projects/zchat/`)，`feat/channel-server-v1` 分支。
代码在 `zchat-channel-server/` submodule 内（`feat/server-v1` 分支）。

## 目标

执行 Phase 4.6 — 架构拆分 + 新功能。这是 Phase Final (pre-release) 之前的最后一批开发任务。

完整计划在 `docs/discuss/plan/06-phase4.6-architecture-split.md`。
架构决策在 `docs/discuss/note/prerelease-todo.md`。
Spec 在 `docs/discuss/spec/channel-server/` 下。

## 当前状态

- Phase 4 完成: engine 七大组件 + protocol + bridge_api + transport + MCP tools + /resolve /status /dispatch handler = 138 tests PASS
- Phase 4.5 进行中: feishu_bridge (另一个 session)
- 你要做的: Phase 4.6 的 5 个 Task（4.6.1 - 4.6.5）

## 工作环境

```bash
cd zchat-channel-server
git checkout feat/server-v1
git checkout -b feat/architecture-split

# 验证基线
uv run pytest tests/ -v
# Expected: 138 tests PASS
```

## 核心架构变更（必须理解）

**之前**: channel-server 作为 MCP server 嵌入每个 agent 的 Claude Code 进程。
**之后**: channel-server 是独立进程（IRC bot + Bridge API），agent 用轻量 agent_mcp.py。

```
channel-server（独立进程）
  ├── IRC bot (nick: cs-bot) → ergo :6667（监听 #conv-* / #squad-* 所有消息）
  ├── Bridge API :9999 ← feishu_bridge
  ├── engine/（ConversationManager + ModeManager + Gate + EventBus + TimerManager）
  └── 路由: IRC 消息前缀解析 → Bridge API 转发

agent_mcp.py（每个 agent 一个进程）
  ├── MCP stdio ↔ Claude Code
  ├── IRC 连接 → ergo（发消息 + 收 @mention）
  └── Tools: reply(edit_of?, side?) / join_conversation / send_side_message
```

**IRC 消息前缀约定**:
- 普通回复: `PRIVMSG #conv-xxx :回复内容`
- 编辑替换: `PRIVMSG #conv-xxx :__edit:msg_003:替换内容`
- side 消息: `PRIVMSG #conv-xxx :__side:建议内容`

**关键约束**: engine/ protocol/ bridge_api/ transport/ 全部 0 改动。只改 server.py + 新建 agent_mcp.py。138 tests 必须继续 PASS。

## 执行方式

按 Task 顺序，每个 Task 走 dev-loop 六步闭环：

### Task 4.6.1: server.py 拆分（阻塞后续所有 Task）

```bash
# Step 1: eval-doc
/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "channel-server 独立化 — server.py 拆分为独立进程 + agent_mcp.py"
# 产出: .artifacts/eval-docs/cs-eval-architecture-split.md

# Step 2: test-plan
/dev-loop-skills:skill-2-test-plan-generator
# 输入: eval-doc + plan/06-phase4.6 Task 4.6.1 的 test-plan 表
# 产出: .artifacts/test-plans/cs-plan-architecture-split.md

# Step 3: test-code
/dev-loop-skills:skill-3-test-code-writer
# 产出: tests/e2e/test_architecture_split.py (6 个测试)

# Step 4: TDD 实现
# 从 server.py (644行) 提取:
#   - MCP 相关代码 (create_server, register_tools, inject_message, poll_irc_queue) → agent_mcp.py
#   - server.py 保留: build_components + wire_bridge_callbacks + IRC bot 路由 + Bridge API
# 新建 agent_mcp.py:
#   - MCP stdio server
#   - Tools: reply (含 edit_of/side 参数, 返回 message_id), join_conversation, send_side_message
#   - IRC 连接: @mention 检测 → inject_message 到 Claude Code
# pyproject.toml: 新增 zchat-agent-mcp entry_point
# E2E conftest.py: channel_server fixture 改为 Popen (非 MCP stdio)
# 注册: /dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-architecture-split

# Step 5: test-run
/dev-loop-skills:skill-4-test-runner
# 回归: uv run pytest tests/unit/ tests/e2e/ -v (138 tests PASS)
# 新增: uv run pytest tests/e2e/test_architecture_split.py -v

# Step 6: artifact registry
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-architecture-split
```

闭环完成标志: cs-report-architecture-split 存在，0 FAIL 0 SKIP，138 回归全 PASS。

### Task 4.6.2: IRC 消息协议（依赖 4.6.1）

```bash
# 六步闭环，artifact ID: cs-*-irc-protocol
# eval-doc 主题: "IRC 消息前缀协议 — __edit: / __side: 前缀解析与路由"
# 实现:
#   agent_mcp.py: reply() 生成 UUID, 按参数组装 IRC 前缀
#   server.py: 新增 parse_irc_prefix() → on_pubmsg 中调用 → 按类型路由到 Bridge API
# 测试: tests/unit/test_irc_message_protocol.py (6个) + tests/e2e/test_message_protocol.py (2个)
```

### Task 4.6.3: Routing 配置（依赖 4.6.1）

```bash
# 六步闭环，artifact ID: cs-*-routing
# eval-doc 主题: "routing.toml 配置 — auto-dispatch + escalation_chain"
# 实现:
#   新建 routing_config.py: RoutingConfig dataclass + load_routing_config()
#   server.py: main() 加载配置 → EventBus 订阅 conversation.created → auto-dispatch default_agents
#   escalation event 检测 → 按 escalation_chain 顺序 dispatch
#   /dispatch handler 增加 available_agents 白名单验证
# 测试: tests/unit/test_routing_config.py (5个) + tests/e2e/test_routing.py (4个)
```

### Task 4.6.4: /review + SLA breach（依赖 4.6.1 + 4.6.3）

```bash
# 六步闭环，artifact ID: cs-*-review-sla
# eval-doc 主题: "/review 统计命令 + SLA breach 单次告警"
# 注意: protocol/commands.py 的 _COMMAND_DEFS 当前无 /review，需先添加 "review": []
# 实现:
#   commands.py: 新增 "review": [] 命令定义
#   server.py _on_admin_command(): /review handler (EventBus.query 聚合昨日统计)
#   EventBus 订阅 sla.breach → Bridge API 发 admin 告警
# 测试: tests/unit/test_review_command.py (3个) + tests/e2e/test_sla_alerts.py (3个)
```

### Task 4.6.5: feishu card+thread 模型（依赖 4.6.2）

```bash
# 六步闭环，artifact ID: cs-*-card-thread
# eval-doc 主题: "feishu_bridge card+thread 模型 + operator 自动 hijack"
# 依赖 Phase 4.5 完成 (feishu_bridge 基础模块)
# 实现:
#   feishu_bridge/visibility_router.py: 重构为 card+thread (ConvThread 映射)
#     - conversation.created → send_card (squad群, thread root)
#     - public → 双写 (customer_chat + squad thread)
#     - side → squad thread only
#     - mode.changed → update_card
#   feishu_bridge/sender.py: 新增 reply_in_thread(root_msg_id, text)
#   feishu_bridge/group_manager.py: 新增 is_operator_in_customer_chat()
#   feishu_bridge/bridge.py: _on_message 检测 auto-hijack
# 测试: feishu_bridge/tests/ (8个 unit) + tests/e2e/test_feishu_card_thread.py (2个 E2E)
```

## 完成标准

全部 5 个 Task 完成后:
```bash
# 1. 回归 (0 regression)
uv run pytest tests/unit/ tests/e2e/ -v

# 2. 新增全部 PASS
uv run pytest tests/unit/test_irc_message_protocol.py tests/unit/test_routing_config.py tests/unit/test_review_command.py -v
uv run pytest tests/e2e/test_architecture_split.py tests/e2e/test_message_protocol.py tests/e2e/test_routing.py tests/e2e/test_sla_alerts.py -v

# 3. entry_points
uv run zchat-channel --help
uv run zchat-agent-mcp --help

# 4. artifact 链条完整
# cs-report-architecture-split / cs-report-irc-protocol / cs-report-routing / cs-report-review-sla / cs-report-card-thread
# 全部存在，0 FAIL 0 SKIP
```

## 提交

每个 Task 完成后在 submodule 内 commit:
```bash
git add -A
git commit -m "feat: Task 4.6.X — <描述>"
```

全部完成后 push:
```bash
git push origin feat/architecture-split
```
```
