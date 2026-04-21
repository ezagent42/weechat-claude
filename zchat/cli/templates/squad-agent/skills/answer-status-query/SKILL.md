---
name: answer-status-query
description: Use when operator asks status questions in squad main chat — "现在几个对话", "conv-001 什么情况", "今天 CSAT", "派 agent". Calls run_zchat_cli, formats response, replies in main chat (not side).
---

# Answer Operator Status Query

## When
operator 主聊里问对话/agent/指标相关。典型：
- "现在有几个进行中的对话"
- "conv-001 什么情况"
- "今天 CSAT 怎么样"
- "把 deep-002 停了"
- "给 conv-005 加个 deep agent"

## Steps
1. **匹配命令**：
   | 意图 | CLI |
   |---|---|
   | 全局对话状态 | `["audit", "status", "--json"]` |
   | 单 conv 详情 | `["audit", "status", "--channel", "<id>", "--json"]` |
   | 指标聚合 | `["audit", "report", "--json"]` |
   | 列 agent | `["agent", "list"]` |
   | 加 agent | `["agent", "create", "<nick>", "--type", "<tpl>", "--channel", "<ch>"]` |
   | 停 agent | `["agent", "stop", "<short-name>"]` |

2. **跑 CLI + 解析**:
   ```
   rc, out, err = run_zchat_cli(args=[...])
   ```

3. **reply** 主聊（普通 reply，**不**用 side）:
   ```
   reply(chat_id="#<my squad channel>", text="<整理后的可读结果>")
   ```

## 边界 · 破坏性操作
- 加 / 停 agent 这类**先确认**：
  ```
  reply(chat_id="#<my squad channel>", text="确认停 yaosh-deep-002？(yes/cancel)")
  ```
  确认后才执行。

## 反模式
- ❌ 用 `side=true` 回 operator（squad 主聊不需要 only-operator 区分；side 会跑去对话 thread 容易丢）
- ❌ 直接 reply 到 `#conv-xxx` 客户对话 channel（你不在那些 channel 里）
- ❌ 替 operator 执行批量停 / 删项目类操作不确认
- ❌ 输出原始 JSON（解析后给可读摘要）
