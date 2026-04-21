---
name: delegate-to-deep
description: Use when customer asks about order status, logistics, customs progress, inventory, CRM data, or any query needing backend lookup. Hard rule from PRD US-2.2 — these queries MUST go through deep peer with placeholder + reply-to chain, NEVER directly to operator.
---

# Delegate to Deep Peer (PRD US-2.2)

## When
客户消息匹配下面任一类（强 trigger）：
- 订单 / 物流 / 清关 / 运单 / 包裹
- 库存 / 现货 / 缺货 / 补货
- 价格深度查询（不在 FAQ 范围）/ 规格参数明细
- 任何需要查后台 / CRM / 知识库的问题

**硬规则**：这类问题**必走 deep peer 委托路径**，**禁止**直接 `@operator` 转人工。理由：本 channel 总有 deep agent 处理后台查询；operator 是处理纠纷/敏感的，把查询转人工 = 破坏 SLA。

## Steps
1. **找 peer**：`list_peers(channel)`，从结果里挑名字含 `-deep-` 的 nick；找不到时用 fallback skill `escalate-to-operator`，不要往下走。

2. **发占位**给客户：
   ```
   placeholder_uuid = reply(chat_id="#<my channel>", text="稍等，正在为您查询...")
   ```
   保留返回的 uuid。

3. **side 召唤 deep peer**（不穿透客户群）：
   ```
   reply(chat_id="#<my channel>",
         text="@<deep_peer_nick> 请查 <客户原问题摘要>，edit_of=<placeholder_uuid>",
         side=true)
   ```

4. **任务结束**。deep peer 用 `edit_of=<placeholder_uuid>` reply 给占位消息。客户视角：
   ```
   稍等，正在为您查询...
     └ 订单 #12345 已发货，快递单号 SF...      （deep 的 reply 挂在占位下）
   ```
   飞书 text 不可原地 patch（API 限制），bridge 把 `__edit:` 语义实现为 `im.v1.message.reply`，
   客户看到"占位 + 展开答复"两层，上下文连续。你不再动作。

## 边界
- 如果 deep 回 `__side:<text>` 给你说"查不到 / 建议走 @operator"，**那时**才切到 `escalate-to-operator` skill
- deep 不会把答案给你转述（PRD 反模式 —— 你是简单模型，转述丢细节）

## 反模式
- ❌ 直接答客户"订单 #X 已发货"（没查就编）
- ❌ 直接 `@operator` 转人工（违反 PRD US-2.2 硬规则）
- ❌ 占位后忘了发 side 委托（客户永远停在"稍等"）
- ❌ side 委托忘带 `edit_of=<placeholder_uuid>`（deep 不知道 reply 挂到哪条）
