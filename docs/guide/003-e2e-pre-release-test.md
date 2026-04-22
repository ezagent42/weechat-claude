# 003 · E2E Pre-Release 真机测试 walkthrough

> 把 V6 sprint 真机走完的 PRD User Story 全部落到可重跑的步骤。每个 TC 给 _前置 / 操作 / 预期 / 验证命令_。

## 0. 测试前置（一次）

跑通 `002-quick-start.md` §0-§5，确保：
- 三 bot 注册成功 + 三 channel + WSS 连接成功
- 4 个 agent running (`zchat agent list`)
- WeeChat `#conv-001` `/names` 看到 `cs-bot`、3 个 agent、你自己

**关于第 4 个测试群** `cs-customer-test`：
- 飞书新建一个空群（你 + 客户那个人），**先不拉 customer bot**
- TC-PR-LazyCreate 时再拉，验证懒创建链路

---

## TC-PR-2.1 · 客户 3 秒首响 (US-2.1)

**前置**: customer bot 在 `cs-customer` 群、conv-001 entry_agent=yaosh-fast-001

**操作**: 客户在 cs-customer 群发：
```
你好，请问发货时间是多久？
```
同时记 T0 = `date +%s.%N`

**预期**:
- ≤3s 客户群收到 bot 回复
- WeeChat `#conv-001` 看到完整链路：
  ```
  cs-bot → @yaosh-fast-001 __msg:om_xxx:你好，请问发货时间是多久？
  yaosh-fast-001 → __msg:<uuid>:您好！我们发货时间是下单后 24 小时内...
  ```
- `cs.log`: `[router] → IRC #conv-001: @yaosh-fast-001 __msg:...`

**验证**: 飞书消息时间戳 - T0 ≤ 3s

---

## TC-PR-2.2 · 复杂查询占位 + 委托链 (US-2.2)

**前置**: 在 conv-001 中加 deep-001：
```bash
uv run zchat agent create deep-001 --type deep-agent --channel conv-001
```

**操作**: 客户发：
```
帮我查订单 #12345 的物流详细到达时间和清关进度
```

**预期** (V6+: reply-to-placeholder 语义):
- ≤1s 客户群收到 fast 占位："稍等，正在为您查询..."
- WeeChat:
  ```
  yaosh-fast-001 → __msg:<uuid-A>:稍等，正在为您查询...
  yaosh-fast-001 → __side:@yaosh-deep-001 请查 #12345 的物流，edit_of=<uuid-A>
  yaosh-deep-001 → __edit:<uuid-A>:订单 #12345 ... [完整答复]   (或 __side:@fast 查不到)
  ```
- 飞书客户群：占位 "稍等..." **下面挂一条** deep 的答复（reply-to 关系）
  - 不是替换；飞书 text 不可 patch 的 trade-off

**反验证**: cs.log **不应**有 `MessageTooLong` traceback（phase 6 修过 IRC sys 截断）

---

## TC-PR-2.3 · squad 卡片 + thread 镜像 (US-2.3)

**前置**: squad bot 在 cs-squad 群，supervises = ["customer"]

**操作**: 客户在 cs-customer 群发任意一条消息

**预期**:
- cs-squad 群自动出现 interactive card
  - title: "对话 cs-customer · 进行中"（用群名，不是 conv id；phase 7 fix）
  - body: 模式 / 客户 字段
  - actions: "接管" / "结案" 按钮
- 后续每条 customer 消息 / agent 回复都在卡片 thread 内镜像
  - 染色 label: `[客户]` / `[AI]` / `[侧栏]`
- operator 在 thread 内回复 → bridge 转 `__side:` 发到 conv-001 → fast 收到并采纳

**验证**: `bridge-squad.log` 应有 `[supervise] card created for conv-001 (msg_id=om_xxx)`

---

## TC-PR-2.5a · @人求助 + 180s timer (US-2.5)

**操作**: 客户发触发人工求助场景：
```
我要投诉客服服务态度，必须今天退款！
```

**预期 ≤10s 内**:
- WeeChat: `yaosh-fast-001 → __side:@operator 客户投诉，超出我处理范围，请接入。`
- WeeChat: `cs-bot → __zchat_sys:{"type":"help_requested",...}` (sla 截断版)
- cs-squad 群：
  - 卡片标题升 "🚨 求助中" 橙色 (phase 4 fix)
  - 卡片 thread 内出现 `<at user_id="all"></at> 🚨 conv-001 求助：@operator ...`
- `cs.log`: `[sla] channel 'conv-001': help wait timer started (180s)`

### 情况 A · operator 在 180s 内回应

**操作**: cs-squad 群点开 conv-001 卡片，进 thread，operator 写：
```
好的，同意退款，已查到订单
```

**预期**:
- bridge 转 `__side:好的，同意退款...` 发到 conv-001
- sla plugin 检测 source=cs-bot 是 human relay → cancel timer
- fast 用 `handle-side-from-operator` skill 采纳并 reply 客户
- `cs.log`: 不应再有 SLA breach

### 情况 B · 静默 180s

**操作**: 触发求助后**别在 thread 回任何话**，等 3 分钟

**预期**:
- 180s 后: `cs.log: [sla] help wait SLA breach after 180s`
- emit `help_timeout` event with reason=`no_human_response` (phase 4 改名)
- cs-squad 卡片变红："⚠️ 求助超时" + thread 提示
- cs-customer 群：fast 发**唯一一次**安抚 "抱歉让您久等..."（不循环）

---

## TC-PR-2.5b · /hijack + /release (US-2.5)

**操作**: cs-squad 群对应卡片点 **"接管"** 按钮

**预期**:
- bridge `_on_card_action` → emit WS message `{channel:"conv-001", content:"/hijack"}`
- mode plugin → mode_changed to=takeover
- 卡片刷新（phase 7 fix `update_multi: true`）：
  - mode 字段："人工接管"
  - 按钮变 "释放 / 结案"
- fast-001 收 `__zchat_sys:mode_changed` → 进副驾驶（`handle-takeover-mode` skill），客户群只发 `__side:`

**操作**: 直接在客户群以人类身份回客户（不加 @）：
```
您好，我是人工小李，看您的订单...
```

**操作**: cs-squad 卡片点 **"释放"** 按钮

**预期**:
- mode_changed to=copilot
- 卡片按钮变回 "接管 / 结案"
- fast 恢复主驾驶

---

## TC-PR-CSAT · 评分链路闭环

**前置**: conv-001 已 takeover 过至少一次

**操作**: cs-squad 卡片点 **"结案"**

**预期**:
- bridge 发 `/resolve` → resolve plugin → emit `channel_resolved`
- csat plugin 订阅 → emit `csat_request`
- customer bridge 在 cs-customer 群发 5⭐ 评分卡（"请为本次服务评分"）

**操作**: 模拟客户在 cs-customer 群点 ⭐⭐⭐⭐ (4 星)

**预期** (phase 7 recall+resend):
- 评分卡**消失**（被 recall）
- 新卡片出现："感谢您的评价 ⭐⭐⭐⭐" 绿色，无按钮
- bridge 不再走 message 通道发 `__csat_score:` —— 走 `csat_score` event 通道（不污染 IRC，phase 7）

**验证**:
```bash
uv run zchat audit status --channel conv-001 --json | jq '.csat_score'   # 期望 4
uv run zchat audit report --json | jq '{total_resolved, escalation_resolve_rate, csat_mean}'
```

---

## TC-PR-3.2 · admin 命令链路

### 3.2a `/status`

**操作**: cs-admin 群发 `/status`

**预期**:
- admin-agent 触发 `handle-status-command` skill
- 调 `run_zchat_cli(["audit", "status", "--json"])` → 解析 → 格式化回复
- cs-admin 群收到可读对话列表

### 3.2b `/dispatch`

**操作**: cs-admin 群发 `/dispatch deep-agent conv-001`

**预期**:
- admin-agent 触发 `handle-dispatch-command` skill
- 先确认："确认派发 deep-agent 到 conv-001，nick=deep-001？(yes/cancel)"
- 你回 `yes`
- 调 `run_zchat_cli(["agent", "create", "deep-001", "--type", "deep-agent", "--channel", "conv-001"])`
- 回复：`✓ deep-agent 已派发到 conv-001`

**验证**: `zchat agent list` 多一行 `yaosh-deep-001`

### 3.2c `/review`

**操作**: cs-admin 群发 `/review`

**预期**: admin 调 `run_zchat_cli(["audit", "report", "--json"])` → 输出 CSAT / 接管率 / 升级转结案率

---

## TC-PR-LazyCreate · 拉新群 → 自动懒创建

**前置**: cs-customer-test 群已建好但 customer bot 未拉入

### 步骤 A · 触发懒创建

**操作**: 飞书把 customer bot 拉进 cs-customer-test

监控：
```bash
tail -f ~/.zchat/projects/prod/bridge-customer.log | grep -iE "bot.added|lazy|chat_info"
tail -f ~/.zchat/projects/prod/cs.log | grep -iE "watcher|reload"
```

**预期 A**:
- `bridge-customer.log: Bot added to group oc_xxx (bot=customer)`
- `bridge-customer.log: [lazy] creating channel=conv-<8字符> agent=conv-<8字符>-agent`
- `cs.log: [watcher] joined new channel #conv-<...>`
- `cs.log: [watcher] routing reloaded: +1 channels`
- `zchat agent list` 多一行 `yaosh-conv-<...>-agent`
- `~/.zchat/projects/prod/routing.toml` 自动 append 新 channel 段

### 步骤 B · 端到端

客户在新群发问 → 验证 ≤3s 收到首响（同 TC-PR-2.1）+ 复杂查询 reply-to 链 + cs-squad 卡片自动出现

### 步骤 C · customer_returned (回访)

**操作**: 在新群结案 + CSAT，等 30s 后客户再发：
```
又有问题
```

**预期**:
- activation plugin emit `customer_returned`
- agent 用 `handle-takeover-mode` skill 表里 `customer_returned` 行：当新会话问候

### 步骤 D · 解散清理

**操作**: 飞书把 customer bot 移出 cs-customer-test 群

**预期**:
- `bridge-customer.log: [disband] removing channel=conv-<...>`
- 子进程调 `zchat channel remove --stop-agents`
- `cs.log: [watcher] parted #conv-<...>`
- `routing.toml` 该条目消失
- `zchat agent list` 该 agent 消失

---

## TC-PR-RoutingDynamic · routing.toml 热加载

**操作**:
```bash
uv run zchat channel create fake-test --bot customer --external-chat oc_fake_xxx
```

**预期 ≤2s**:
- `cs.log: [watcher] joined new channel #fake-test + routing reloaded: +1`

**清理**:
```bash
uv run zchat channel remove fake-test
# cs.log 应再有 -1 reload
```

---

## TC-PR-3.1 · CLI 数据层

**前置**: 跑过若干轮对话 + ≥1 takeover + ≥1 resolve

```bash
uv run zchat audit status --json | jq
uv run zchat audit status --channel conv-001 --json | jq
uv run zchat audit report --json | jq
```

**预期 schema**：
- `status` → `{channels: {conv-xxx: {state, takeovers[], message_count, csat_score, ...}}, aggregates: {...}}`
- `report` → `{total_channels, total_takeovers, total_resolved, escalation_resolve_rate, csat_mean}`
- 全部字段**无业务名**（无 customer/operator key）

---

## 验收门槛

| TC | 通过判据 |
|---|---|
| 2.1 | T1-T0 ≤ 3s |
| 2.2 | 占位 + reply-to-placeholder 链路完整 |
| 2.3 | squad 卡片 title=群名 + thread 镜像 |
| 2.5a-A | timer cancel + agent 采纳 |
| 2.5a-B | 180s 后 SLA breach + 安抚仅 1 次 |
| 2.5b | 接管/释放按钮反向切换 |
| CSAT | csat_score 入 audit + thank-you 卡显示 |
| LazyCreate A-D | 4 步全过 |
| RoutingDynamic | 2s 内 reload |
| 3.x | 4 个 admin 命令全部触发对应 skill |

跑完贴 `cs.log` + 三 `bridge-*.log` 给开发审计。

## 失败排查速查

参考 `002-quick-start.md` §10。常见问题：
- 卡片不刷新：检查 card config `update_multi: true`（phase 7）
- CSAT 卡点了无变化：可能漏了 recall+resend 路径，看 bridge log
- agent 不响应：先看 `agent_manager._auto_confirm_startup` 是否被新版 Claude prompt 卡住
