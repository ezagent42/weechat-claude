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

## TC-PR-V7 · Plugin 架构回归套件

V7（2026-04-22）引入 `plugin_loader` 后专项回归。针对 **已经跑过业务场景** 的 prod 项目做，不需要额外搭环境。

### V7-1 · CS 启动时 6 plugin 全注册

**操作**：`zchat down && zchat up` 后 attach 到 zellij 的 `cs` tab。

**预期**（cs.log 前 20 行）：

```
INFO plugin_loader plugin 'activation' registered
INFO plugin_loader plugin 'audit' registered
INFO plugin_loader plugin 'csat' registered
INFO plugin_loader plugin 'mode' registered
INFO plugin_loader plugin 'resolve' registered
INFO plugin_loader plugin 'sla' registered
INFO boot [boot] registered 6 plugins: ['activation','audit','csat','mode','resolve','sla']
```

**失败排查**：
- 缺某 plugin → `src/plugins/<name>/plugin.py` 的 `name` 属性和目录名不一致
- `pass 2`（deferred）再也没 register → csat `__init__` 的 kw `audit` 没对上签名 DI

### V7-2 · Plugin state 新路径落盘（非 V6 位置）

**前置**：跑过 TC-PR-2.1（客户发过消息）。

**验证**：

```bash
# 新路径存在 + 有数据
ls ~/.zchat/projects/prod/plugins/audit/state.json
jq '.channels["conv-001"].message_count' ~/.zchat/projects/prod/plugins/audit/state.json
# 期望：数字 ≥1

# V6 老路径不存在（已被迁移或迁移后未被重建）
test ! -f ~/.zchat/projects/prod/audit.json && echo "OK"
test ! -f ~/.zchat/projects/prod/activation-state.json && echo "OK"
```

**失败排查**：若老路径又出现 → 仍有代码在 V6 位置写文件（不应该），grep plugin 源码查 `persist_path|state_file=`。

### V7-3 · CSAT → Audit 签名驱动 DI（跨 plugin 写同一文件）

**前置**：跑完 TC-PR-CSAT（客户给过 5⭐）。

**验证**：

```bash
# csat_score 必须写入 audit plugin 的 state.json（证明 csat 拿到了 audit 引用）
jq '.channels["conv-001"].csat_score' ~/.zchat/projects/prod/plugins/audit/state.json
# 期望：5
```

**失败排查**：若返回 `null` → `plugin_loader._resolve_init_kwargs` 没把 audit 注入 csat 的 `audit` kw 参数；grep `cs.log` 看 csat 是否是在 pass 1 还是 pass 2 注册。

### V7-4 · plugins.toml 配置覆盖生效

**操作**：改 `~/.zchat/projects/prod/plugins.toml`：

```toml
[plugins.sla]
takeover_timeout = 10   # 从 180 改到 10
help_timeout = 10
```

`zchat down && zchat up` 重启，然后：
1. 点 squad 卡片 "接管"
2. **不做任何事**等 10 秒

**预期**：
- `cs.log`: `[sla] channel 'conv-001': takeover SLA breach after 10s`（**10s，不是 180s**）
- 自动 emit `/release` → mode 回 copilot

**失败排查**：若仍 180 秒 → config 没透进 SlaPlugin。手动：

```bash
cd zchat-channel-server
uv run python -c "from plugins.sla.plugin import SlaPlugin; p = SlaPlugin({'takeover_timeout': 10}, None, None); print(p._timeout_seconds)"
# 期望：10.0
```

**测完改回 180**：

```toml
[plugins.sla]
takeover_timeout = 180
help_timeout = 180
```

### V7-5 · CS 重启后 plugin state 恢复

**前置**：跑过若干轮对话 + ≥1 takeover + ≥1 resolve + ≥1 csat。

**操作**：

```bash
zchat audit status --json | jq '.aggregates' > /tmp/before.json

zchat down && sleep 2 && zchat up
sleep 10

zchat audit status --json | jq '.aggregates' > /tmp/after.json

diff /tmp/before.json /tmp/after.json && echo "OK: audit state survived restart"
```

**预期**：`diff` 无输出，aggregates 完全一致。

**失败排查**：
- 数据归零 → audit plugin 的 `_load` 读错路径（或 data_dir 被错误 override）
- 部分字段丢 → write-to-tmp + atomic rename 被打断，看有没有 `.tmp` 残留文件

### V7-6 · 临时禁用 plugin 生效

**操作**：改 `plugins.toml` 加 `enabled = false`：

```toml
[plugins.activation]
enabled = false
```

`zchat down && zchat up`，然后：

**验证**：
- `cs.log`: `plugin 'activation' disabled via plugins.toml; skip`
- `[boot] registered 5 plugins: [...]`（5，不是 6，且列表无 activation）
- 后续 customer 在 dormant channel 发消息 → **不再** emit `customer_returned` event（activation 没加载）

**测完还原**：删掉那一段或改 `enabled = true`。

### V7-7 · V6 → V7 数据迁移演练（可选，非 prod 环境）

**目的**：验证老用户升级路径，不在 prod 直接跑（会污染 prod 数据）。在新建测试项目做：

```bash
zchat project create v7-migrate-test
# 模拟 V6 残留
cat > ~/.zchat/projects/v7-migrate-test/audit.json <<'EOF'
{"channels": {"legacy-conv": {"state": "resolved", "csat_score": 4, "message_count": 10, "takeovers": []}}}
EOF

# 迁移
cd ~/.zchat/projects/v7-migrate-test
mkdir -p plugins/audit
mv audit.json plugins/audit/state.json

# 验证 V7 能读
cd ~/projects/zchat/zchat-channel-server
uv run python -c "
import asyncio
from channel_server.plugin import PluginRegistry
from channel_server.plugin_loader import load_plugins, load_plugins_toml
async def check():
    r = PluginRegistry(); n = lambda *a, **k: None
    load_plugins(registry=r, plugins_toml={},
                 routing_path='$HOME/.zchat/projects/v7-migrate-test/routing.toml',
                 injections={'emit_event': n, 'emit_command': n})
    status = r.get_plugin('audit').query('status', {'channel': 'legacy-conv'})
    assert status['csat_score'] == 4, f'FAIL: {status}'
    print('OK: V6 → V7 readable')
asyncio.run(check())
"

# 清理
rm -rf ~/.zchat/projects/v7-migrate-test
```

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
| V7-1 | cs.log 有 6 plugin registered + boot 汇总 |
| V7-2 | state.json 在 `plugins/audit/` 新路径 |
| V7-3 | audit state.json 里 csat_score 被 csat 写入 |
| V7-4 | sla takeover 按 plugins.toml 配置 10s 超时 |
| V7-5 | `zchat down && zchat up` 后 aggregates 不变 |
| V7-6 | `enabled=false` 后 5 plugins + 无 customer_returned |

跑完贴 `cs.log` + 三 `bridge-*.log` 给开发审计。

## 失败排查速查

参考 `002-quick-start.md` §10。常见问题：
- 卡片不刷新：检查 card config `update_multi: true`（phase 7）
- CSAT 卡点了无变化：可能漏了 recall+resend 路径，看 bridge log
- agent 不响应：先看 `agent_manager._auto_confirm_startup` 是否被新版 Claude prompt 卡住
