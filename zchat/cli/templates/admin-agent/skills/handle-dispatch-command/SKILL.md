---
name: handle-dispatch-command
description: Use when admin types `/dispatch <agent-type> <channel>` or asks "派一个 deep agent 到 conv-001". Confirms intent, then calls run_zchat_cli agent create. Destructive — must confirm before executing.
---

# Handle /dispatch Command

## When
- `/dispatch deep-agent conv-001`
- 自然语言: "派一个 deep 到 conv-001", "给 conv-002 加个翻译 agent"

## Steps
1. **解析参数**：agent type + 目标 channel + 推断的 short nick（如 `deep-001`）。

2. **确认（强制）**：
   ```
   reply(chat_id="#<my admin channel>",
         text="确认派发 <agent-type> 到 <channel>，nick=<short-name>？回复 yes 执行 / cancel 取消")
   ```
   等管理员确认。

3. **执行**（确认后）：
   ```
   rc, out, err = run_zchat_cli(args=[
       "agent", "create", "<short-nick>",
       "--type", "<agent-type>",
       "--channel", "<channel>",
   ])
   ```

4. **回报**：
   ```
   if rc == 0:
       reply(chat_id="#<my admin channel>", text="✓ <agent-type> 已派发到 <channel>")
   else:
       reply(chat_id="#<my admin channel>", text=f"✗ 派发失败: {err}")
   ```

## 反模式
- ❌ 不确认就执行（破坏性，nick 起错没法回滚）
- ❌ 自己起 nick 不告诉管理员（"我决定叫它 X" → 失控）
- ❌ 执行成功后没回 reply（管理员不知道有没有跑）
