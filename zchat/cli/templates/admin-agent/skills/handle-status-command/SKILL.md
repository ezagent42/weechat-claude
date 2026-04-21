---
name: handle-status-command
description: Use when admin types `/status` or asks "现在多少对话" / "active conv" / "进行中的对话". Calls run_zchat_cli audit status --json then formats per-conv summary + aggregates.
---

# Handle /status Command

## When
- 管理员发 `/status` 或 `/status <channel-id>`
- 自然语言: "现在多少对话", "看看活跃对话", "什么在进行"

## Steps
1. **取数**（按是否带 channel 参数分支）：
   ```
   # 全局
   rc, out, err = run_zchat_cli(args=["audit", "status", "--json"])
   
   # 单 channel
   rc, out, err = run_zchat_cli(args=["audit", "status", "--channel", "<channel>", "--json"])
   ```

2. **解析 JSON**: `{"channels": {...}, "aggregates": {...}}`

3. **格式化** reply：
   ```
   reply(chat_id="#<my admin channel>", text="""
   当前进行中对话: <N> 个
   - <conv-id>: <mode>，已 <duration>，<message_count> 条消息
   - ...
   聚合: 接管 <takeovers> 次 / CSAT <csat> / 升级转结案率 <rate>%
   """)
   ```

## 反模式
- ❌ 直接 `reply` 原始 JSON 让管理员自己看
- ❌ rc != 0 时不告知错误，假装成功
