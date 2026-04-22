---
type: code-diff
id: code-diff-v6-finalize-phase5
phase: 5
trigger: eval-doc-012
status: completed
date: "2026-04-21"
section: §3.2 完整化（chat_name 跨 bridge 传递）
title: "chat_info 系统事件：customer bridge 拉群名 → squad bridge 缓存 → 卡片标题"
---

# Phase 5 · chat_info 跨 bridge 传递

## 范围

补完 eval-doc-012 完成判据 #5（"customer bridge 首次见 conv 调 get_chat_info 拿群名进 metadata"）。

设计选择：**用现有 `__zchat_sys` event 机制传递**，**不**扩 `ws_messages` schema 加 metadata 字段。理由：保持"channel + format"二元抽象，不引入第三种通道；`build_event` 的 `data: dict` 字段已是开放式 payload。

## 改动

### `zchat-channel-server/src/feishu_bridge/sender.py`
- import `GetChatRequest` from `lark_oapi.api.im.v1`
- 新方法 `get_chat_info(chat_id) -> dict | None` — 调 `im.v1.chat.get`，返回 `{name, description, avatar}`；失败/异常静默返回 None

### `zchat-channel-server/src/feishu_bridge/bridge.py`
- `__init__`: 加 2 个新字段
  - `_chat_info_emitted: set[str]`（去重，每 chat_id 只 lazy 拉一次）
  - `_supervised_chat_names: dict[str, str]`（监管 bridge 用：channel_id → chat_name）
- `_on_message`: 首次见 chat_id → `_chat_info_emitted.add` + 调 `_emit_chat_info(channel_id, chat_id)`
- 新方法 `_emit_chat_info`: `sender.get_chat_info` → `bridge_client.send(build_event("chat_info", {chat_name, chat_id}))`
- `_handle_sys_event`: 加 `event_name == "chat_info"` 分支 → 缓存 `_supervised_chat_names[conv_id] = chat_name`
- `_supervise_help_requested`: 卡片 metadata 加 `chat_name=self._supervised_chat_names.get(conv_id, "")`
- `_supervise_help_timeout`: 同上加 chat_name
- `_handle_supervised_message`: 首次建 thread root card 时也加 chat_name

### feishu_renderer 已 phase 4 就绪
`build_conv_card` 已支持 `metadata["chat_name"]` → title 优先用群名 + conv_id + 状态。

## 数据流

```
飞书客户群发消息
  → customer bridge `_on_message`
  → 首次：lazy 调 get_chat_info → emit chat_info event 到 CS
  → CS WS broadcast → squad bridge `_on_bridge_event`
  → supervised path → `_handle_sys_event(event="chat_info")`
  → squad cache `_supervised_chat_names[conv_id] = chat_name`

后续 squad 建 card 或 update_card：
  → 用 cache 取 chat_name → 进 metadata → renderer 渲染 title
  → 飞书 squad 群卡片 title = "对话 cs-customer · conv-001 · 进行中" 而非 "对话 conv-001 · 进行中"
```

## 死代码

无（本 phase 是新增能力，无删除）。

## 业务术语红线

- ✅ `sender.get_chat_info` 是 lark_oapi 包装，业务层（feishu_bridge/）自带业务知识，允许
- ✅ 事件名 `chat_info` 通用，不绑定客服业务
- ✅ `_supervised_chat_names` 只缓存 channel_id → string，不绑定 role

## 测试结果

| Suite | Before | After | Δ |
|---|---|---|---|
| zchat-channel-server unit | 181 | 181 | 0 (新增能力无新断言；lazy + best-effort) |
| zchat CLI unit | 325 | 325 | 0 |
| zchat-protocol unit | 32 | 32 | 0 |

无回归。

## 完成判据 mapping

| # | Promise | Phase 5 完成 |
|---|---|---|
| 5 | customer bridge 首次见 conv 调 `get_chat_info` 拿群名进 metadata | ✅ 用 chat_info 系统事件传给 squad bridge metadata |

## 关联 artifacts

- 上游：eval-doc-012, code-diff-v6-finalize-phase4
- 收尾：所有 15 项完成判据满足

## 实战联动

PRD TC-PR-2.5 求助通知链验收时，squad 群卡片 title 应该是"对话 `<飞书群名>` · conv-001 · 🚨 求助中"而非纯 conv id；customer 群名要求至少一条客户消息进 customer bridge 后才生效（lazy）。
