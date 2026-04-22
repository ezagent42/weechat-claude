---
name: handle-takeover-mode
description: Use when receiving `__zchat_sys:mode_changed` system event with `to=takeover` or `to=copilot/auto`. Toggles between copilot mode (only side, never __msg) and normal mode (resume __msg replies to customer).
---

# Handle Mode Change

## When
进来 `__zchat_sys:<json>` 且 json 含：
- `event: "mode_changed"`，`data.to: "takeover"` —— operator 接管，进副驾驶
- `event: "mode_changed"`，`data.to: "copilot"` 或 `"auto"` —— operator 释放，恢复主驾驶

## Steps · takeover 模式
1. **停止**用 `__msg:` 发客户消息。任何 `reply` 都加 `side=true`。
2. 继续监听客户消息，但回复**只送 squad thread**（operator 看），客户不可见。
3. 内容偏向**给 operator 的辅助**：术语解释、客户上下文整理、建议话术草稿。

```
reply(chat_id="#<my channel>",
      text="客户上一条意图：<解读>。建议回复：<草稿>",
      side=true)
```

## Steps · copilot/auto 模式
1. 恢复正常：客户消息 → 普通 `reply`（默认 `__msg:`）
2. 如果 takeover 期间有未答客户消息，发个续接：
   ```
   reply(chat_id="#<my channel>", text="<针对客户最后一句的承接>")
   ```

## 其它系统事件（mode 之外）速查
| event | 行为 |
|---|---|
| `channel_resolved` | 对话结案。**不要**主动发言。后续客户再发用 `customer_returned` 处理 |
| `customer_returned` | 已结案 channel 客户回访 → 当新会话，问候 + 询问需求 |
| `help_timeout` | 见 `escalate-to-operator` skill 第 3 步 |
| `sla_breach` | takeover 超时自动 release → 恢复接管 + 续接客户 |

## 反模式
- ❌ takeover 期间还用 `__msg:` 回客户（违反"operator 接管"语义）
- ❌ takeover 期间不发任何东西（应继续 side 给 operator 提供 context）
- ❌ 收到 sys 事件就 `reply(...)` 答复（sys 是状态通知，不是用户消息）
