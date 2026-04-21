---
type: code-diff
id: code-diff-v6-finalize-phase2
phase: 2
trigger: eval-doc-012
status: completed
date: "2026-04-21"
section: §3.4
title: "routing.toml agents 死字段清理"
---

# Phase 2 · routing.toml agents 死字段清理

## 范围

`agents` 字段（channel→role→nick map）从 V4 起就在 routing.toml 写入，但 V6 router 已不读它（router 只用 `entry_agent`）。本 phase 把这个死字段彻底删除：写入侧不写、读取侧不读、测试同步更新、prod routing.toml 手清。

## 改动

### `zchat/cli/routing.py`
- `add_channel`: 删 `default_agents` 参数 + 删 `entry["agents"] = {}` 初始化
- `join_agent`: 签名从 `(project_dir, channel_id, role, nick, *, as_entry=False)` 改成 `(project_dir, channel_id, nick, *, as_entry=False)` —— role 参数删除（只用作 agents map 的 key，map 死了 role 也死）
- `join_agent` 行为：仅在 `as_entry=True` 或 channel 还无 entry_agent 时写 `entry_agent` 字段；不再 `setdefault("agents", {})` / 写 `agents_map[role] = nick`
- 模块顶部 docstring 更新：明示 routing.toml 不存 agents，roster 由 IRC NAMES 反映

### `zchat/cli/app.py`
- `cmd_agent_create`: 删 `--role` option，调用 `routing_join_agent(pdir, channel, scoped)`（不传 role）
- `cmd_agent_join`: `--role` 改为 `--as-entry`（语义匹配新行为）
- `cmd_channel_create`: 删 `--default-agents` option
- `cmd_channel_list`: 删 `agents=[...]` 显示列

### `zchat-channel-server/src/channel_server/routing.py`
- `ChannelRoute` 数据类删 `agents: dict[str, str]` 字段
- `RoutingTable` 删 `channel_agents()` 方法
- `load()` 不再从 toml 读 `agents` 字段（V6 兼容：旧 toml 里若有 agents 段，读时静默忽略）
- 模块顶部 V6 schema 文档更新：channel→agents 不存 routing；roster 由 IRC NAMES 反映

### Test 改动
- `zchat-channel-server/tests/unit/test_routing.py`：
  - V6_TOML fixture 去掉 `[channels."ch-1".agents]` 段
  - `test_load_basic_channels`：删 `assert ch1.agents == {...}`
  - **删** `test_channel_agents`（测的是已删函数）
  - `test_channel_route_defaults`：删 `assert route.agents == {}`
  - `test_backward_compat_no_entry_agent_field`：删 `assert ch.agents == {...}`
- `zchat-channel-server/tests/unit/test_router.py`：
  - 重命名 `make_routing_with_agents` → `make_routing_with_entry`，签名只接 entry_agent
  - 多处 caller 更新（6 处）
  - `test_copilot_mode_without_entry_agent_drops_message`: 直接构造 ChannelRoute 不再传 agents
- `zchat/tests/unit/test_routing_cli.py`：
  - **删** `test_join_agent_registers_nick`、`test_join_agent_multiple_roles`、`test_join_agent_overwrites_existing_nick`（测的都是已删 agents map 写入）
  - **新增** `test_join_does_not_write_agents_field`（断言新 join_agent 不写 agents）
  - `test_first_join_auto_sets_entry` / `test_second_join_does_not_override_entry` / `test_join_as_entry_overrides` / `test_set_entry_agent` / `test_join_agent_unknown_channel_raises`：签名更新 (3-arg)
  - `test_add_channel_minimal`：断言改成空 dict 而非 `{"agents": {}}`
  - `test_add_channel_with_all_fields` / `test_list_channels_includes_all_fields`：default_agents → entry_agent
- `zchat/tests/unit/test_channel_cmd.py`：
  - `test_routing_roundtrip`：join_agent 签名 + 断言 entry_agent
  - `test_routing_add_channel_with_default_agents` → `test_routing_add_channel_with_entry_agent`
  - `test_channel_create_with_default_agents` → `test_channel_create_with_entry_agent`
  - `test_channel_list_formats`：default_agents → entry_agent
  - `test_agent_join_updates_routing` → `test_agent_join_sets_entry`（断言 entry_agent）
  - `test_agent_join_with_explicit_role` → `test_agent_join_as_entry_overrides`（验证新 --as-entry option）

### `~/.zchat/projects/prod/routing.toml`
手动删除 3 个 channel 段下的 `[channels."#xxx".agents]` 子段（保留 entry_agent）。

## 死代码清理

- `RoutingTable.channel_agents()` —— 删
- `ChannelRoute.agents` 字段 —— 删
- `add_channel(default_agents=...)` 参数 —— 删
- `--default-agents` CLI option —— 删
- `--role` / `-r` CLI option（agent create/join）—— 删
- `cmd_channel_list` 的 agents 显示 —— 删

## 业务用语红线

- ✅ `zchat-channel-server/src/channel_server/routing.py` 无业务术语（customer/operator/...）
- ✅ `zchat/cli/routing.py` 无业务术语
- ✅ `zchat/cli/app.py` channel/agent 命令无业务术语

## 测试结果

| Suite | Before | After | Δ |
|---|---|---|---|
| zchat-channel-server unit | 180 | 179 | -1 (test_channel_agents) |
| zchat CLI unit | 332 | 330 | -2 (净) |

无回归。

## 关联 artifacts

- 上游：eval-doc-012, code-diff-v6-finalize-phase1
- 下游：code-diff-v6-finalize-phase3 (§3.2 help_requested 通知链)

## 完成判据 mapping

| # | Promise | Phase 2 满足 |
|---|---|---|
| 10 | routing.py 删 agents 字段 + channel_agents 函数 + 测试 | ✅ |
| 11 | prod routing.toml 清理 agents 段 | ✅ |
| 12 | 架构红线 routing/CLI 无业务术语 | ✅ |
| 13 | unit tests 全绿 | ✅ |
