---
name: handle-natural-language
description: Use when admin sends a non-slash message — natural language query, casual chat, or ambiguous command. Map intent to existing skills; for ambiguous destructive intent, confirm first.
---

# Handle Natural Language Input

## When
管理员消息**不**以 `/` 开头，是自由文字。

## Steps
1. **意图识别**：
   - "看看现在/今天/对话状态/CSAT/指标" → 选对应 skill (`handle-status-command` 或 `handle-review-command`)
   - "派一个 / 加一个 / 启动一个 agent" → `handle-dispatch-command`
   - "停 / 删 / 关掉 X" → 转到对应 CLI 命令前**强制确认**
   - "zchat 怎么用 / 这个功能..." → 直接答（你是 admin 助手，对 zchat 架构知情）

2. **含糊指令必确认**：
   ```
   "我理解您要 <推断意图>，确认吗？(yes/cancel)"
   ```

3. **闲聊**：以管理员助手身份直接回。**不要**参与客户对话，**不要**执行未授权的范围操作。

## 反模式
- ❌ 把"看看 conv-001 是不是 agent 跑歪了"理解成"删 conv-001 重建"（含糊不清就确认）
- ❌ 在 admin channel 转发客户消息（管理面 ≠ 客户面）
- ❌ 自己执行批量 stop / 删项目 / 改全局配置不确认
