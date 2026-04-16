# Bridge API Protocol v2 设计提案

> 基于 pre-release 测试和协议 review 的发现，重新设计 Bridge API 协议。
> 核心原则：**基础设施和业务分离**。

---

## 当前协议的问题

### 业务概念泄漏到协议层

| 泄漏点 | 当前 | 问题 |
|--------|------|------|
| 消息类型命名 | `customer_message` / `operator_message` / `admin_command` | 角色名硬编码在 type 中 |
| 字段命名 | `customer` / `operator_id` / `admin_id` | 每种角色不同的字段名 |
| reply 类型 | 只有一种 `reply`，无 sender 信息 | 出站方向丢失了发送者身份 |
| 可见性路由表 | `{"public": {"customer", "operator", "admin"}}` | 角色名硬编码 |
| Gate 规则 | `(COPILOT, OPERATOR) → SIDE` | 模式名 + 角色名硬编码 |
| 命令类型 | `operator_command` vs `admin_command` | 按角色分类而非按功能 |
| CSAT 评分 | 塞在 `customer_message` 里 | 混用消息类型 |

### 入站/出站不对称

| 方面 | 入站 (bridge→cs) | 出站 (cs→bridge) |
|------|-----------------|------------------|
| 发送者 | 隐含在消息类型中 | 无 sender 信息 |
| 可见性 | 无 | 必须带 visibility |
| 时间戳 | 无 | 无 |
| 消息 ID | 可选 | 必须 |

---

## v2 协议设计

### 核心原则

1. **统一的消息格式** — 入站出站用同一种 `message` 类型
2. **sender_id 标识来源** — 不区分 customer/operator/agent，由 Bridge 自己识别
3. **visibility 由 Gate 引擎决定** — 不在协议中硬编码路由规则
4. **命令是消息的子类型** — 不按角色分类
5. **可扩展的 audience 机制** — 替代角色名硬编码

### 消息格式

#### 入站（bridge → channel-server）

**会话生命周期**
```json
{
  "type": "connect",
  "conversation_id": "conv_123",
  "sender_id": "user_abc",
  "metadata": {"source": "feishu", "name": "David"}
}
```

**消息**
```json
{
  "type": "message",
  "conversation_id": "conv_123",
  "sender_id": "user_abc",
  "text": "你好",
  "message_id": "msg_001",
  "timestamp": "2026-04-17T00:34:47Z"
}
```

**命令**
```json
{
  "type": "command",
  "conversation_id": "conv_123",
  "sender_id": "user_xyz",
  "command": "/hijack",
  "timestamp": "2026-04-17T00:35:00Z"
}
```

**全局命令（无 conversation）**
```json
{
  "type": "command",
  "sender_id": "admin_001",
  "command": "/status",
  "timestamp": "2026-04-17T00:36:00Z"
}
```

#### 出站（channel-server → bridge）

**消息回复**
```json
{
  "type": "message",
  "conversation_id": "conv_123",
  "sender_id": "fast-agent",
  "text": "套餐价格如下...",
  "visibility": "public",
  "message_id": "cs_msg_001",
  "timestamp": "2026-04-17T00:34:50Z"
}
```

**消息编辑**
```json
{
  "type": "edit",
  "conversation_id": "conv_123",
  "message_id": "cs_msg_001",
  "text": "更新后的内容",
  "timestamp": "2026-04-17T00:35:10Z"
}
```

**状态事件**
```json
{
  "type": "event",
  "event_type": "mode.changed",
  "conversation_id": "conv_123",
  "data": {"from": "auto", "to": "copilot", "triggered_by": "user_xyz"},
  "timestamp": "2026-04-17T00:35:00Z"
}
```

### 关键变化

| 当前 v1 | v2 | 说明 |
|---------|-----|------|
| `customer_message` / `operator_message` | `message` | 统一类型，靠 `sender_id` 区分 |
| `customer_connect` | `connect` | 去掉角色名 |
| `operator_command` / `admin_command` | `command` | 统一类型 |
| `reply` | `message` | 入站出站同一种格式 |
| 无 sender_id（出站） | 有 `sender_id` | Bridge 可以判断是谁发的 |
| 无 timestamp | 有 `timestamp` | 全链路时间追踪 |
| `customer` / `operator` 字段 | `sender_id` + `metadata` | 去角色化 |
| `csat_score` 塞在消息里 | 独立消息类型或 metadata | 不混用 |

### 可见性路由

v2 中 channel-server 的可见性路由表变为**配置驱动**：

```toml
# routing.toml
[visibility]
# audience tag → 哪些 bridge capability 能收到
public = ["*"]                    # 所有 bridge
side = ["operator", "admin"]      # 排除 customer capability
system = ["operator", "admin"]    # 同 side
```

Bridge 注册时声明自己的 capabilities（audience tags）：
```json
{"type": "register", "instance_id": "fb-1", "capabilities": ["customer"]}
```

channel-server 根据 visibility → capabilities 匹配表决定发给哪些 bridge。**匹配逻辑是基础设施，tag 名称是配置**。

### Gate 规则配置化

```toml
# routing.toml
[[gate_rules]]
mode = "copilot"
sender_role = "operator"       # Bridge 可以在 metadata 中传 role hint
forces_visibility = "side"

[[gate_rules]]
mode = "takeover"
sender_role = "agent"
forces_visibility = "side"
```

channel-server 的 Gate 引擎从配置加载规则，不硬编码在代码中。

### Bridge adapter 的职责

```
feishu_bridge 只做：
  入站：飞书消息 → identify sender_id → message(sender_id, text)
  出站：收到 message(sender_id, visibility, text)
        → 根据 sender_id 判断是客户还是 agent（Bridge 自己的映射）
        → 根据 visibility 决定发到哪个飞书群
        → 渲染格式（card / thread / 纯文本）

feishu_bridge 不做：
  不判断角色（channel-server 不需要知道 customer/operator）
  不决定可见性（channel-server 的 Gate 决定）
  不处理命令（只转发 command 到 channel-server）
```

---

## 迁移路径

### Phase 1（当前可做）
- reply 加 `sender_id` 字段（向后兼容）
- CSAT 分离为独立消息类型
- ws_server.py 可见性路由表改为从配置加载

### Phase 2（v2 协议）
- 统一 `message` 类型替代 `customer_message` / `operator_message` / `reply`
- 统一 `command` 类型替代 `operator_command` / `admin_command`
- `connect` 替代 `customer_connect`
- Gate 规则配置化

### Phase 3（完全解耦）
- 移除所有角色名硬编码
- Bridge capabilities 完全配置驱动
- 支持自定义角色扩展

---

## 与当前 Bug 的关系

| Bug | v2 如何解决 |
|-----|-----------|
| #conv- channel 未创建 | connect 消息正确触发 → channel-server 创建 channel（基础设施逻辑） |
| 客户消息不在 squad thread | 出站 message 带 sender_id，Bridge 判断 sender=customer → 写 thread |
| 卡片按钮报错 | command 类型统一，card action 转为 command(sender_id, "/hijack") |
| SLA 告警不可读 | connect 时 metadata 带 name，event 的 data 带 metadata |
| 消息重复 | message_id 去重（Bridge 层职责不变） |
