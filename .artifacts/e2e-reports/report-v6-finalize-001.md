---
type: e2e-report
id: e2e-report-v6-finalize-001
trigger: eval-doc-012
status: completed
date: "2026-04-21"
covers:
  - code-diff-v6-finalize-phase1
  - code-diff-v6-finalize-phase2
  - code-diff-v6-finalize-phase3
  - code-diff-v6-finalize-phase4
  - code-diff-v6-finalize-phase5
  - code-diff-v6-finalize-phase6
  - code-diff-v6-finalize-phase7
---

# E2E Report · V6 Finalize

## Summary

| Suite | Result |
|---|---|
| `zchat/tests/unit/` | **325 passed** |
| `zchat-channel-server/tests/unit/` | **181 passed** |
| `zchat-protocol/tests/` | **32 passed** |
| **Total** | **538 passed / 0 failed** |

无 skip，无 xfail，无 flaky。

## 完成判据 final mapping (eval-doc-012 §完成判据)

| # | Promise | 满足 | 实施位置 |
|---|---|---|---|
| 1 | 4 PRD template soul.md ≤30 行 + skills/ + start.sh cp 双副本 (CLAUDE.md + skills) | ✅ | phase 1 |
| 2 | `instructions.md` 删 read soul.md 弱间接 | ✅ | phase 1 |
| 3 | sla plugin 检测 `@operator/@人工/...` emit `help_requested` event | ✅ | phase 4 |
| 4 | squad bridge 订阅 → `update_card "🚨 求助中"` + `reply_in_thread <at user_id="all"></at>` | ✅ | phase 4 |
| 5 | customer bridge 首次见 conv 调 `get_chat_info` 拿群名进 metadata | ✅ | phase 5 (用 chat_info 系统事件传递，零 protocol schema 改) |
| 6 | `feishu_renderer.build_conv_card` title 用 metadata `chat_name` | ✅ (fallback 已实现) | phase 4 |
| 7 | bridge sender 加自发消息过滤 | ✅ | phase 4 |
| 8 | `agent_mcp.py` 新增 `list_peers(channel)` MCP tool | ✅ | phase 3 |
| 9 | `channel_server/router.py` `@entry` 前 NAMES check，不在则 emit help_requested | ✅ | phase 3 |
| 10 | `routing.py` 删 `agents` 字段写入 + `channel_agents` 函数 + 对应测试 | ✅ | phase 2 |
| 11 | 既有 `~/.zchat/projects/prod/routing.toml` 清理 `agents` 段 | ✅ | phase 2 |
| 12 | 架构红线：core/protocol/CLI 中**禁止**业务命名 | ✅ | phase 1-4 |
| 13 | unit tests 全绿 | ✅ | 538 passed |
| 14 | 死代码扫描零命中 | ✅ | 见下 |
| 15 | evidence chain 注册 registry.json | ✅ | eval-doc-012 + phase 1-4 + 本 report |

**15/15 全部满足。** #5 通过 phase 5 用 `chat_info` 系统事件机制完成，无需扩 protocol schema。

## 死代码 grep 验证

| Pattern | core (`channel_server/`) | protocol | CLI (`zchat/cli/` 除 templates) |
|---|---|---|---|
| `channel_agents` | 0 | 0 | 0 |
| `GroupsConfig` | 0 | 0 | 0 |
| `GroupManager` | 0 | 0 | 0 |
| `_forward_customer/operator/admin` | 0 | 0 | 0 |
| `identify_role` | 0 | 0 | 0 |
| `admin_chat_id` | 0 | 0 | 0 |
| `default_agents` | 0 | 0 | 0 |
| `_channel_server_defaults` | 0 | 0 | 0 |
| `customer/operator/admin/squad/feishu` | 0 | 0 | 0 (templates 允许) |

## Phase 总览

| Phase | Section | 改动 | 测试 Δ |
|---|---|---|---|
| 0 (pre-loop) | cleanup | 删 send_message_as_operator + GroupManager 别名 + V4 era pre_release/ 整目录 | -2 channel-server |
| 1 | §3.1 | 4 PRD template 重构成 soul (~25 行) + 13 SKILL.md；start.sh 加 CLAUDE.md + skills cp；instructions.md 弱间接删除 | 0 |
| 2 | §3.4 | routing.toml `agents` 死字段彻底删；join_agent 签名瘦身；`--default-agents`/`--role` CLI option 删 | -1 channel-server / -2 zchat |
| 3 | §3.3 | agent_mcp `list_peers` MCP tool；CS irc_connection NAMES/JOIN/PART 缓存；router NAMES 熔断 (fail open on 空缓存) | +2 channel-server |
| 4 | §3.2 + 业务术语清理 | sla emit help_requested；squad bridge handle event；feishu_renderer 加 help states；bridge 自发过滤；删 channel_server 死配置；audit 业务名 blocklist 替换 | -5 zchat (删整文件) |
| 5 | §3.2 完整化 | chat_info 系统事件：customer bridge get_chat_info → emit；squad bridge 缓存 + 卡片 metadata 传递 chat_name；零 protocol schema 改 | 0 |

## 业务/红线复查

详见 `code-diff-v6-finalize-phase4.md` §业务术语红线扫描结果表。

## 不在本 sprint 实施（deferred）

- **占位卡片化**（`v6-placeholder-card-edit-design.md`）：飞书 text msg 不可 patch，需占位发卡片 + 撤回。涉及 zchat / zchat-channel-server / zchat-protocol 三仓联调，另排 sprint。
- **基础 `templates/claude/`**：用户决策保持原样。
- **V7 entry-as-coordinator 多 agent workflow chain**（`v7-entry-as-coordinator.md`）：Socialware 接入。

## 关联文档

- 设计：`docs/discuss/008-v6-finalize-plan.md`
- eval-doc：`eval-doc-012` (`.artifacts/eval-docs/eval-v6-finalize-012.md`)
- code-diffs：phase 1-4
- 备份：`.local-backup/credentials-20260421-094316/` + `.local-backup/routing-20260421-094316.toml`

## 状态

V6 finalize sprint 实施完成。
