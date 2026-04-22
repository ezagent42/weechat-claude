---
name: handle-mode-event
description: Use when receiving `__zchat_sys` events `mode_changed` / `channel_resolved` / `customer_returned` / `sla_breach`. Broadcasts a compact one-liner in squad main chat so operators stay aware.
---

# Handle Conv Lifecycle Events

## When
sys event 类型属下表：

| event | 主聊播报模板 |
|---|---|
| `mode_changed` to=`takeover` | `📌 conv-<id> 已被 operator 接管` |
| `mode_changed` to=`copilot` 或 `auto` | `▶️ conv-<id> 已恢复 agent 主驾驶` |
| `channel_resolved` | `✅ conv-<id> 对话结案` |
| `customer_returned` | `🔁 conv-<id> 客户回访（已结案后又来）` |
| `sla_breach` | `⏱️ conv-<id> takeover 超时自动 release` |

## Steps
1. 解析 sys event 的 `event` + `data.channel` + 必要字段。
2. 主聊 `reply`（普通，不 side），用上表模板：
   ```
   reply(chat_id="#<my squad channel>", text="<模板填好>")
   ```

## 边界
- 这些事件**信息密度低**，单行播报即可，**不要**展开长解释
- `customer_returned` 比较关键，可附一句"建议看一下卡片"（让 operator 决定是否介入）

## 反模式
- ❌ 把 sys event 原 JSON 输出
- ❌ 同一 event 触发多次播报（去重：用 (event, channel) 做 key）
- ❌ 因为 mode_changed 就主动 reply 到 conv channel "我来接管"（你不在那个 channel）
