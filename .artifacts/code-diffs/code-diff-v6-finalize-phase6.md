---
type: code-diff
id: code-diff-v6-finalize-phase6
phase: 6
trigger: eval-doc-012
status: completed
date: "2026-04-21"
section: 运行时观察驱动的 3 个修正
title: "sla false-positive / IRC sys MessageTooLong / edit→reply-to-placeholder 语义"
---

# Phase 6 · 3 个运行时观察驱动的修正

## 触发

pre-release 实跑 TC-PR-2.2/2.5 观察到 3 个问题：

1. **sla false-positive**：deep 在 side 里说"@yaosh-fast-001 ... 建议走 @operator 流程" → sla plugin 子串匹配误触发 help_requested
2. **CS traceback**：`irc.client.MessageTooLong: 512 bytes` —— `__zchat_sys:help_requested` payload 含完整 `data.text`（中文长串），JSON `\uXXXX` 转义后超 512 字节
3. **飞书侧占位没展开/没撤回**：V7-deferred 的占位卡片方案太重（三仓联调），用户决策改走"reply-to-placeholder"—— `edit_of` 不再尝试 `update_message patch`（text 消息飞书 API 不支持），改 `reply_in_thread` 把答复挂在占位下

## 改动

### Fix A · sla plugin `HELP_REQUEST_MARKERS` 严格化

`src/plugins/sla/plugin.py`：
- 加 `_FIRST_AT_RE = re.compile(r"@\S+")`
- 新函数 `_first_at_is_help_marker(text)`：仅当 text 第一个 @-mention 属于 markers 才返回 True
- `on_ws_message` 用 `_first_at_is_help_marker(text)` 替代 `any(marker in text for marker in HELP_REQUEST_MARKERS)` 子串匹配

效果：
```
"@operator 客户要求退款..."           → first_at = "@operator"   → ✅ 触发
"@yaosh-fast-001 建议走 @operator ..." → first_at = "@yaosh-fast" → ❌ 不触发 (正确)
```

### Fix B · IRC sys payload 截断 + encode_sys UTF-8 化

`zchat-protocol/zchat_protocol/irc_encoding.py`：
- `encode_sys(payload)` 的 `json.dumps` 加 `ensure_ascii=False` —— 中文保留 UTF-8 (3 bytes/char) 而非 `\uXXXX` (6 bytes/char)，给 IRC 512 byte PRIVMSG 留足余量

`zchat-channel-server/src/channel_server/router.py`：
- 新模块常量 `_IRC_SYS_TEXT_BYTES_LIMIT = 200` + `_IRC_SYS_TEXT_FIELDS = ("text", "content", "message")`
- 新函数 `_slim_for_irc(data)`：对 data 浅拷贝，对这三个字段按 UTF-8 字节截断 + 加 "…" 结尾
- `emit_event` 的 IRC sys 路径：用 `_slim_for_irc(data)` 而非 raw data 构造 payload
- WS 路径**不截断** —— bridges 需要 full text

### Fix C · bridge on_edit 改 `reply_in_thread`（语义重定义）

`zchat-channel-server/src/feishu_bridge/outbound.py`：
- `OutboundRouter.on_edit`：从 `sender.update_message(feishu_msg_id, text)` 改为 `sender.reply_in_thread(feishu_msg_id, text)`
- docstring 更新：说明飞书 `message.patch` 仅支持 card，V6+ 把 `__edit:` 语义重定义为 `reply-to-placeholder`（客户视角"占位 + 展开答复"两层）

**协议不变**：`zchat-protocol` `__edit:<cs_msg_id>:<text>` 继续沿用，语义由 bridge 侧实现决定。

### 4 个 skill 文档同步

措辞从"就地替换占位"改成"挂到占位下作为 reply"：
- `templates/fast-agent/skills/delegate-to-deep/SKILL.md`
- `templates/deep-agent/skills/handle-delegation/SKILL.md`
- `templates/fast-agent/skills/escalate-to-operator/SKILL.md` (help_timeout 安抚也挂占位下)
- `templates/deep-agent/skills/escalate-no-data/SKILL.md`

现存 agent workspace (`~/.zchat/projects/prod/agents/yaosh-{fast,deep}-001/`) 同步 cp 新 `CLAUDE.md` + `.claude/skills/`。

### 设计 note 标记 superseded

`docs/discuss/010-v6-placeholder-card-edit-design-SUPERSEDED.md` 顶部加 SUPERSEDED 标签，指向 phase 6 reply-to-placeholder 方案，保留作历史决策记录。

## 测试

新增 / 修改 3 个测试：
- `test_outbound_router.py::test_edit_with_msg_id_calls_reply_in_thread` (重命名 + 改断言)：`on_edit` 调 `sender.reply_in_thread(...)`，不再调 `update_message`
- `test_outbound_router.py::test_edit_without_mapping_noop`：都不调
- `test_sla_plugin.py::test_agent_to_agent_side_with_quoted_operator_does_not_trigger`：deep 给 fast 的 side 里 quote "@operator" 不触发 help_timer（回归 false-positive）
- `test_router.py::test_emit_event_truncates_long_text_for_irc`：300 字中文 text → WS 保留 full；IRC sys payload encoded ≤ 462 bytes + 含 "…"

## 死代码

无。

## 业务用语红线

仍然干净 (channel_server/ + protocol/ 无业务名)。

## 测试结果

| Suite | Before | After | Δ |
|---|---|---|---|
| zchat-channel-server unit | 181 | 183 | +2 (new: truncate + false-positive；edit 测试重写计为 0) |
| zchat CLI unit | 325 | 325 | 0 |
| zchat-protocol unit | 32 | 32 | 0 |

无回归。

## 关联 artifacts

- 上游：e2e-report-v6-finalize-001
- 触发：pre-release 实跑 2026-04-21 15:00-15:02 WeeChat/CS 日志
- 关联 note：`v6-placeholder-card-edit-design.md` → SUPERSEDED
