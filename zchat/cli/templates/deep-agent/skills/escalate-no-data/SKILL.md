---
name: escalate-no-data
description: Use when the delegated query has no data in any tool/knowledge base — must NOT fabricate. Replies via side to fast peer recommending operator escalation, instead of sending edit_of with made-up content under the placeholder.
---

# Escalate When No Data

## When
- 委托问题用尽所有工具、知识库都查不到
- 数据存在但语义不明确，强行答会误导客户

## Steps
1. **不要**用 `edit_of=<placeholder_uuid>` 给客户编造答复（会挂个虚假 reply 到占位下）。

2. 给 fast peer 发 side，建议走人工：
   ```
   reply(chat_id="#<conv channel>",
         text="@<fast peer nick> 查不到 <主题>，建议走 @operator 流程。edit_of=<原 placeholder_uuid> 的占位由你接管 reply。",
         side=true)
   ```

3. 任务结束。fast 收到这条 side 后会切到 `escalate-to-operator` skill，自己在占位下 reply 安抚 + 发 `@operator`。

## 反模式
- ❌ 编造"订单 #12345 已发货"应付（反幻觉硬约束）
- ❌ 自己直接发 `@operator side`（你不在 operator 视野中，应该让 fast 触发整个 escalate 流程）
- ❌ 用 `edit_of=<placeholder_uuid>` 写"我也查不到"挂到占位下（占位应由 fast 接管挂转人工提示，不该由你发）
