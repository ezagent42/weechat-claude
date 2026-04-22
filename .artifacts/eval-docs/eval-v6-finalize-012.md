---
type: eval-doc
id: eval-doc-012
status: confirmed
producer: skill-5
created_at: "2026-04-21T00:00:00Z"
mode: simulate
feature: v6-finalize-skills-help-router
submitter: yaosh
related:
  - test-plan-013
spec: docs/discuss/008-v6-finalize-plan.md
plan: docs/discuss/008-v6-finalize-plan.md
related_notes:
  - docs/discuss/009-v6-help-request-notification-design.md
  - docs/discuss/010-v6-placeholder-card-edit-design-SUPERSEDED.md  # deferred
  - docs/discuss/011-v7-entry-as-coordinator.md
---

# Eval: V6 收尾整合（skills 拆分 + help_requested + router 熔断 + 死字段清理）

## 基本信息

- 模式：模拟（pre-impl evaluation）
- 提交人：yaosh
- 日期：2026-04-21
- 状态：confirmed
- 基线：refactor/v4 分支 HEAD（commit fe38222）
- 设计文档：`docs/discuss/008-v6-finalize-plan.md`
- 实施计划：同上 §3.1-§3.4
- 工作量预估：~3.6 人日

## 背景

V6 pre-release 测试（TC-PR-2.1 / 2.2 / 2.5）暴露 5 个根因（详见 v6-finalize-plan.md §1）：

1. soul.md 过长 → 4 个 PRD agent 不可靠遵循 → §3.1 拆 skills
2. template 没有 CLAUDE.md → Claude Code 不自动加载 → §3.1 cp 兼带 CLAUDE.md
3. `@operator` 求助没通知 → §3.2 sla emit + squad bridge `<at all>`
4. routing.toml `agents` 字段死代码 → §3.4 删除
5. router 没熔断（entry agent 离线消息丢） → §3.3 NAMES 检查 + emit help_requested

第 6 个根因（飞书 text 消息不可 patch / PRD US-2.2 占位 edit）需占位卡片化方案，**deferred to V7+**（用户 2026-04-21 决策：跨三个仓库不好调试）。

## 4 项实施

### §3.1 · 4 PRD agent template 重构成 soul + skills

**变更点**：
- soul.md 砍到 ~25 行，仅描述人格 + Voice + 边界 + 工具 + skills 索引
- 现 soul.md 决策树拆成 `.claude/skills/<name>/SKILL.md`，YAML frontmatter `description` 触发关键词
- 4 个 template 的 `start.sh` 加 `cp soul.md → CLAUDE.md` + `cp -r skills/ .claude/skills`
- 4 个 template 的 `settings.local.json.permissions.allow` 加 `"Skill"`
- `zchat-channel-server/instructions.md` 删 "read soul.md if exists" 弱间接段
- **不动** `templates/claude/`（基础模板保持）

**预计 SKILL.md 文件**：
- fast-agent: delegate-to-deep / escalate-to-operator / handle-side-from-operator / handle-takeover-mode
- deep-agent: handle-delegation / escalate-no-data
- admin-agent: handle-status-command / handle-review-command / handle-dispatch-command / handle-natural-language
- squad-agent: answer-status-query / handle-help-event / handle-mode-event

合计 14 个 SKILL.md。可用 `/skill-creator` 半自动生成骨架。

### §3.2 · help_requested 通知链（PRD US-2.5）

详见 `v6-help-request-notification-design.md`，6 个改动模块（sla plugin emit / customer bridge get_chat_info / squad bridge update_card + reply_in_thread <at all> / feishu_renderer / sender filter / help_timeout payload）。

### §3.3 · Router 层熔断 + list_peers MCP 原语

详见 `v7-entry-as-coordinator.md` 的子集：router NAMES 熔断 + IRC presence query + `list_peers(channel)` MCP tool。zchat / Socialware 边界严格遵守（zchat 只提供 nick 列表，不做 skill metadata）。

### §3.4 · routing.toml `agents` 死字段清理

`zchat/cli/routing.py join_agent` 不再写、删 `channel_agents` 函数；`zchat-channel-server/src/channel_server/routing.py` `ChannelRoute.agents` 字段删除；既有 prod routing.toml 手清；删 `test_channel_agents` 测试用例。

## 不做（deferred）

- 占位卡片化（v6-placeholder-card-edit-design.md → V7+）
- 基础 `templates/claude/` 不动
- V7 主题（多 agent chain / Socialware 接入 / supervises 复杂语法）

## 完成判据（completion promise）

只有当**全部满足**时才能宣布 V6 收尾完成：

1. 4 个 PRD agent template 的 soul.md 缩到 ≤ 30 行 + 对应 skills/ 目录创建 + start.sh 加 `cp` 双副本（CLAUDE.md + skills）
2. `zchat-channel-server/instructions.md` 删 "read soul.md" 弱间接段
3. SLA plugin 检测 `@operator` emit `help_requested` event
4. squad bridge 订阅 `help_requested` → `update_card` 加"🚨 求助中" + `reply_in_thread` 用 `<at user_id="all"></at>`
5. customer bridge 首次见 conv 调 `get_chat_info` 拿群名进 metadata
6. `feishu_renderer.build_conv_card` title 用 metadata `customer_chat_name`
7. bridge sender 加自发消息过滤
8. `agent_mcp.py` 新增 `list_peers(channel)` MCP tool
9. `channel_server/router.py` `@entry` 前检查 NAMES，不在则 emit `help_requested`
10. `routing.py` 删 `agents` 字段写入 + `channel_agents` 函数 + 对应测试
11. 既有 `~/.zchat/projects/prod/routing.toml` 清理 `agents` 段
12. **架构红线**：core/protocol/CLI 中**禁止**出现 `customer` / `operator` / `admin` / `squad` / `feishu` 等业务命名
13. **测试**：channel-server unit + zchat unit 全绿
14. **死代码扫描**：grep `channel_agents|GroupsConfig|GroupManager|_forward_customer|_forward_operator|_forward_admin|identify_role|admin_chat_id` 在生产代码（src/）零命中
15. evidence chain 完成：本 eval-doc + test-plan-013 + 各阶段 code-diff + 最终 e2e-report 注册到 `registry.json`

## 关联 artifacts（待生成）

- test-plan-013（依据本 eval-doc 生成）
- code-diff-v6-finalize-phase{1..N}
- e2e-report-v6-finalize-001
