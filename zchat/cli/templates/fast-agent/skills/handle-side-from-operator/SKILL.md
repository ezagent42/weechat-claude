---
name: handle-side-from-operator
description: Use when receiving a message of form `__side:<text>` WITHOUT `@<my-nick>` prefix. This is operator's copilot suggestion forwarded by bridge from squad thread; adopt it and reply to customer.
---

# Handle Operator Side Suggestion

## When
进来一条消息，**完全匹配以下结构**：
```
__side:<text>           ← 注意：text 不是以 @<我的 nick> 开头
```
sender 一般是 `cs-bot` 或 bridge 的 IRC nick。**不要**用 sender 做判别，看消息结构。

> 反例（**不**触发本 skill）：
> - `__side:@yaosh-fast-001 ...` —— 点名指令，按指令执行（不是采纳建议）
> - `__msg:<uuid>:...` —— 客户消息

## Steps
1. **不要质疑发送者身份**。bridge 转发的就是 operator 副驾驶建议（squad 群 thread 内 operator 写的内容），是真有效建议。

2. 把 side text 当作 operator 给你的建议草稿，**用客户语言重新组织**后 `reply` 给客户：
   ```
   reply(chat_id="#<my channel>", text="<整理后的回复>")
   ```

3. 如果 operator 建议明显需要委托查后端（例如 "请帮客户查订单 #X"），先发占位 + side 委托 deep（参考 `delegate-to-deep` skill），不要自己编。

## 边界
- side 内容是**给你的提示**，不是直接发客户的成品 —— 必要时润色
- 但**不要曲解** operator 意图。如果 operator 说"告诉客户明天发货"，就照实告诉客户
- side 内容里如果有 `@operator` 等内部标记，去掉再发客户

## 反模式
- ❌ 因为 sender 是 cs-bot 就忽略 side（V6 架构 operator 没 IRC 身份，所有 side 都从 bridge 来）
- ❌ 把 side 原文不加修饰直接 reply 客户（包含内部标记 / 不通顺）
- ❌ 用 `side=true` 回 operator 的 side（变成只 operator 看，客户没收到）
