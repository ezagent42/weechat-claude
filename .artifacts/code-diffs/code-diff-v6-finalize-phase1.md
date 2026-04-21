---
type: code-diff
id: code-diff-v6-finalize-phase1
phase: 1
trigger: eval-doc-012
status: completed
date: "2026-04-21"
section: §3.1
title: "4 PRD agent template 重构 soul + skills"
---

# Phase 1 · 4 PRD agent template 重构 soul + skills

## 范围

| Template | soul.md (lines) | skills/ |
|---|---|---|
| fast-agent | 35 | delegate-to-deep / escalate-to-operator / handle-side-from-operator / handle-takeover-mode |
| deep-agent | 30 | handle-delegation / escalate-no-data |
| admin-agent | 36 | handle-status-command / handle-review-command / handle-dispatch-command / handle-natural-language |
| squad-agent | 35 | answer-status-query / handle-help-event / handle-mode-event |

合计：4 soul.md（all ≤ 36 行人格），13 SKILL.md（PRD 决策树拆分）。

## 改动详情

### 4 个 template 的 soul.md
全量重写，从 80~130 行决策树砍到 ≤36 行人格 + Voice + 输入分类 + Tools + skills 索引。

### 4 个 template 新建 skills/<name>/SKILL.md
每个 SKILL.md 标准结构：YAML frontmatter (name + description "Use when ...") + When + Steps + 反模式。description 全部"Use when..." 起头，符合 Claude Code skills CSO 规范，按关键词触发。

### 4 个 template start.sh 同步改 3 处
- `cp soul.md → CLAUDE.md`（Claude Code 自动加载）
- `cp -r skills/ → .claude/skills/`（Skill 工具按 description 触发）
- `settings.local.json.permissions.allow` 加 `mcp__zchat-agent-mcp__list_peers` + `Skill`

### `zchat-channel-server/instructions.md`
删 "## SOUL File / read soul.md if exists" 弱间接段；改成 "Persona + Skills" 简介，明示 CLAUDE.md 自动加载、SKILL.md 按 description 触发。

## 死代码清理（同步）

无新死代码（本 phase 是新增 + 重写，不留旧 soul.md 残骸）。

注：Phase 0（pre-loop cleanup）已删：
- `send_message_as_operator` 测试包装方法 + 测试
- `GroupManager` V5 别名 + 反向兼容测试
- 整个 V4 era `zchat-channel-server/tests/pre_release/`（broken at import + V5 schema）

## 业务用语红线

- ❌ 检查 `zchat/cli/templates/` —— **允许**业务名（template 是给 deployed agent 的，可以提 customer/operator/squad/admin/feishu）
- ❌ 检查 `zchat-channel-server/instructions.md` —— **允许** operator 等术语（这是给 deployed agent 的提示，是业务层）
- ✅ 检查 `zchat-channel-server/src/channel_server/` —— 本 phase 未触
- ✅ 检查 `zchat-protocol/` —— 本 phase 未触
- ✅ 检查 `zchat/cli/` (除 templates 外) —— 本 phase 未触

## 测试结果

| Suite | Before | After |
|---|---|---|
| zchat-channel-server unit | 180 ✓ | 180 ✓ |
| zchat CLI unit | 332 ✓ | 332 ✓ |

无回归。

## 关联 artifacts

- 上游：eval-doc-012
- 下游：code-diff-v6-finalize-phase2 (§3.2 help_requested 通知链)

## 完成判据 mapping (eval-doc-012)

| # | Promise | Phase 1 满足 |
|---|---|---|
| 1 | 4 PRD template soul.md ≤30 行 + skills/ + start.sh cp 双副本 | ✅ (lines 30/35/35/36) |
| 2 | instructions.md 删 read soul.md 弱间接 | ✅ |
| 13 | unit tests 全绿 | ✅ |
