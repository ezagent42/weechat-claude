---
name: handle-delegation
description: Use when receiving `__side:@<my-nick> ... edit_of=<uuid>` from fast peer — perform backend/knowledge query then reply with edit_of=<uuid> to attach your answer under fast's placeholder as a thread reply (PRD US-2.2).
---

# Handle Fast → Deep Delegation

## When
进来一条消息匹配：
```
__side:@<my-nick> <委托内容>，edit_of=<placeholder_uuid>
```
- sender 是 fast peer（nick 形如 `<user>-fast-xxx`）
- 关键字段：**委托内容** + `edit_of=<placeholder_uuid>`

## Steps
1. **解析**委托内容（订单号、查询主题）+ 抽出 `<placeholder_uuid>`。

2. **查询**：用你可用的工具 / 知识库 / `run_zchat_cli`。给自己合理时间，不要怠工。

3. **用 `edit_of` 把答复挂到 fast 的占位消息下** —— `edit_of` 必须用刚才抽到的 uuid：
   ```
   reply(chat_id="#<conv channel>",
         text="<完整答复，给客户看的最终版本>",
         edit_of="<placeholder_uuid>")
   ```
   → bridge 发 `__edit:<uuid>:<text>` → 飞书调 `im.v1.message.reply` 把你的答复作为
   reply 挂在占位下。客户视角：
   ```
   稍等，正在为您查询...          （fast 的占位）
     └ 订单 #1234 已发货...      （你的答复 reply 在下面）
   ```

4. 任务结束，**不再发**。

## 边界 · 缺 edit_of
若 fast 漏带 `edit_of=<uuid>`：
- **不要**自己直接 `reply __msg:` 给客户（会出现两条独立消息，违反 PRD US-2.2）
- 用 side 反询问：
  ```
  reply(chat_id="#<conv channel>",
        text="@<fast peer nick> 没收到 edit_of uuid，你来 reply 客户吧",
        side=true)
  ```

## 边界 · takeover 模式
收到 `__zchat_sys:mode_changed to=takeover`：进副驾驶 only side（不 `edit_of` 替换 fast，等 operator 释放）。

## 反模式
- ❌ 把答案 `side=true` 发给 fast 让 fast 转述（PRD 反模式：简单模型转述丢细节）
- ❌ 不带 `edit_of` 就发 `__msg:`（变成独立新消息，不挂在占位下，客户看不到上下文关联）
- ❌ 重复 fast 占位文本（"稍等..." + 答复）—— 直接给最终答复就好
- ❌ 假装查到的数据（查不到时走 `escalate-no-data` skill）
