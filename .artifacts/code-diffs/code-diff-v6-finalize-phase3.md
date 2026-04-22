---
type: code-diff
id: code-diff-v6-finalize-phase3
phase: 3
trigger: eval-doc-012
status: completed
date: "2026-04-21"
section: §3.3
title: "Router NAMES 熔断 + list_peers MCP tool"
---

# Phase 3 · Router NAMES 熔断 + list_peers MCP tool

## 范围

- CS router 在 `@<entry>` 前用 IRC NAMES 检查 entry 是否真实在 channel；不在 → emit `help_requested` 系统事件而非空 @
- 新增 MCP tool `list_peers(channel)` — agent 查同 channel 其它 nick（用于 entry-as-coordinator workflow，让 fast-agent 等 entry agent 动态发现 deep peer 而非硬编码 nick）

## 改动

### `zchat-channel-server/src/channel_server/irc_connection.py`
- `IRCConnection.__init__`: 加 `_members: dict[str, set[str]]` 字段
- `connect()` 内部新增 5 个 IRC 事件 handler：
  - `namreply` (RPL_NAMREPLY 353) — 初始 NAMES 反弹时 populate 成员集合
  - `join` — 新成员加入 channel
  - `part` — 成员主动离开
  - `quit` — 成员断连（清除全部 channel 中该 nick）
  - `nick` — 成员改名
- 新方法 `names(channel) -> set[str]` — router 查 channel 当前成员

### `zchat-channel-server/src/channel_server/router.py`
- `forward_inbound_ws` 在 copilot/auto 模式下 `@entry` 前两段 check：
  1. `entry_agent` 字段为空 → emit `help_requested {reason: "no_entry_agent"}` (替代旧 "drop + log warning")
  2. `_irc.names(irc_channel)` 已 populated 但 entry 不在其中 → emit `help_requested {reason: "entry_offline", entry: <nick>}`
  - 空 NAMES 缓存 (启动期未收 NAMES reply) → fail open (允许 @)，避免假阳性

### `zchat-channel-server/agent_mcp.py`
- `_start_irc(... members=None)`: 新增 members 参数；caller 传入 dict 引用
- 注册 5 个 IRC 事件 handler 同 CS 端，维护 caller 提供的 members 字典
- `state["members"] = members_map`：MCP server 启动时把 members map 装入 state，tool handler 通过 closure 拿到
- 新 MCP tool `list_peers(channel)`：
  - 输入：`channel` (含/不含 `#` 都行)
  - 输出：JSON list 排序后的 peer nick (剔除 self + service nicks `cs-bot`)
- 新 handler `_handle_list_peers(members, arguments)`

### Tests
新增 2 个 router 测试：
- `test_copilot_mode_entry_offline_emits_help_requested`：MockIRCConnection 用 members={"#general": {"cs-bot"}}，断言 router 不 @ 而 emit help_requested with reason=entry_offline
- `test_copilot_mode_entry_present_does_not_short_circuit`：members 含 entry，断言正常 @entry，无 help_requested

旧测试 `test_copilot_mode_without_entry_agent_drops_message` 重命名为 `..._emits_help_requested`，断言改成 emit help_requested with reason=no_entry_agent。

`MockIRCConnection` 加 `__init__(members=...)` + `names(channel)` 方法支持。

## 死代码清理

无（本 phase 是新增能力）。

## 业务用语红线

- ✅ irc_connection.py / router.py 无业务术语
- ✅ agent_mcp.py 引入 `_SERVICE_NICKS = {"cs-bot"}` —— 这是 IRC service nick，是 zchat 基础设施约定，**不是**业务命名
- ✅ list_peers tool description 不含业务术语

## 测试结果

| Suite | Before | After | Δ |
|---|---|---|---|
| zchat-channel-server unit | 179 | 181 | +2 (entry-offline + entry-present) |

无回归。

## 关联 artifacts

- 上游：eval-doc-012, code-diff-v6-finalize-phase2
- 下游：code-diff-v6-finalize-phase4 (§3.2 help_requested 通知链)

## 完成判据 mapping

| # | Promise | Phase 3 满足 |
|---|---|---|
| 8 | agent_mcp.py 新增 list_peers MCP tool | ✅ |
| 9 | router NAMES 熔断 + emit help_requested | ✅ |
| 12 | core/CLI 无业务术语 | ✅ |
| 13 | unit tests 全绿 | ✅ |

## 实战联动

- fast-agent template 的 `delegate-to-deep` SKILL.md 已在 §3.1 写好"先 list_peers 找 deep peer"步骤，本 phase 提供了底层支撑
- §3.2 help_requested 通知链将订阅本 phase router emit 的事件 → squad bridge 转发到飞书
