---
name: handle-help-event
description: Use when receiving `__zchat_sys:help_requested` (some conv asked human) or `help_timeout` (180s passed without operator response). Broadcasts in squad main chat so operators in the room see it.
---

# Handle Help Events

## When
- `__zchat_sys` event 含 `event: "help_requested"` —— 某 conv channel 的 fast 发了 `@operator` 求助
- `__zchat_sys` event 含 `event: "help_timeout"` —— 180s 内 operator 没响应

## Steps · help_requested
1. **不**直接 reply 这条 sys 事件。
2. 在 squad 主聊播报，让 operator 即时看到：
   ```
   reply(chat_id="#<my squad channel>",
         text="🚨 conv-<id> (<chat_name>) 求助:\n<原求助文本>\n请进卡片 thread 写副驾驶建议或点'接管'按钮")
   ```
   字段从 sys event 的 `data` 取（`channel`, `text`, `customer_chat_name` 等）。

## Steps · help_timeout
```
reply(chat_id="#<my squad channel>",
      text="⚠️ conv-<id> 求助超时（180s 无响应），可能需要您跟进")
```

## 边界
- bridge 那一侧会同时 update_card 加"🚨 求助中" + 在卡片 thread `<at user_id="all"></at>` —— 你这边的主聊广播是**冗余通知**，确保 operator 多一道感知。
- 不要因为 bridge 已通知就跳过你这条主聊播报（不同入口效果不同）。

## 反模式
- ❌ 用 `side=true`（squad 主聊不需要）
- ❌ 自己 `reply` 到 conv channel 想"帮忙提示"（你不在 conv channel）
- ❌ 重复播报同一 help_requested（如果收到多次相同事件，去重；用 channel id 做 dedupe key）
