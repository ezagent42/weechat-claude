# PRD: WeeChat-Claude — 基于 WeeChat 和 Claude Code Channels 的本地多 Agent 协作系统

**版本**: 3.1.0
**作者**: Allen (ezagent42)
**日期**: 2026-03-21
**状态**: Draft

> **术语约定**: 本文档中与 WeeChat 概念重叠的术语一律遵循 WeeChat 命名惯例：
> - **channel** (非 "room") — 群聊 buffer，对应 WeeChat 的 channel 类型
> - **private** (非 "DM") — 私聊 buffer，对应 WeeChat 的 private 类型
> - **buffer** — WeeChat 中的消息容器，channel 和 private 都是 buffer 的子类型
> - **nick** — 用户昵称，与 WeeChat nick 概念一致

-----

## 1. 产品概述

### 1.1 一句话描述

一个由三个独立组件构成的本地/局域网多 Agent 协作系统：WeeChat 用户通过 Zenoh P2P 消息总线，与一个或多个 Claude Code 实例进行实时对话、任务分配和协作编程。

### 1.2 问题陈述

Claude Code Channels（research preview, 2026-03-20）支持 Telegram/Discord 作为消息桥接，但对以下场景不够理想：

- **本地路由**：zenohd 作为轻量本地路由，数据不出本机/内网
- **多 Agent 管理**：同时运行和管理多个 Claude Code 实例
- **终端原生**：在 tmux/terminal 中完成一切
- **可组合**：各组件独立使用，不强制绑定

### 1.3 设计原则

**关注点分离**：三个组件通过 Zenoh topic 约定通信，互不知道对方的实现细节。

```
场景 1：人 ↔ 人（只装 weechat-zenoh）
┌─────────┐  Zenoh  ┌─────────┐
│ WeeChat │ ◄─────► │ WeeChat │
│ + zenoh │         │ + zenoh │
│ (Alice) │         │ (Bob)   │
└─────────┘         └─────────┘

场景 2：人 ↔ Agent（weechat-zenoh + weechat-channel-server）
┌─────────┐  Zenoh  ┌───────────────────┐
│ WeeChat │ ◄─────► │ weechat-channel   │
│ + zenoh │         │ (MCP server)      │
│ (Alice) │         │    ↕ stdio        │
└─────────┘         │ Claude Code       │
                    └───────────────────┘

场景 3：完整部署（三个组件全装）
┌─────────────────────────────────┐
│ WeeChat                         │
│  weechat-zenoh.py   (P2P 通信)  │
│  weechat-agent.py   (Agent 管理)│
└────────┬────────────────┬───────┘
         │  Zenoh mesh    │ subprocess
    ┌────▼────┐      ┌───▼──────────┐
    │ WeeChat │      │ Claude Code  │
    │ (Bob)   │      │ + channel    │
    └─────────┘      │ (agent0)     │
                     └──────────────┘
```

-----

## 2. 组件总览

|组件                        |类型               |语言    |运行方式                     |依赖                            |
|--------------------------|-----------------|------|-------------------------|------------------------------|
|**weechat-zenoh**         |WeeChat Python 脚本|Python|`/python load`           |eclipse-zenoh                 |
|**weechat-agent**         |WeeChat Python 脚本|Python|`/python load`           |weechat-zenoh（通过 WeeChat 命令交互）|
|**weechat-channel-server**|Python MCP server (Claude Code plugin)|Python|Claude Code plugin       |mcp, eclipse-zenoh            |

-----

## 3. 组件 1：weechat-zenoh

### 3.1 定位

WeeChat 的 Zenoh P2P 聊天基础设施。提供 channel/private buffer 管理、消息收发、在线状态追踪。**不知道 Claude Code 的存在**——任何 Zenoh 节点（人类、Agent、bot）对它而言都是平等的 participant。

### 3.2 Zenoh Key Expression 设计

```
wc/                                  # 根前缀
  channels/
    {channel_id}/
      messages                       # Channel 消息 (pub/sub)
      presence/{nick}                # Channel 成员在线状态 (liveliness)
  private/
    {sorted_pair}/                   # Private 通道（alice_bob，字母序拼接）
      messages                       # Private 消息 (pub/sub)
  presence/
    {nick}                           # 全局在线状态 (liveliness)
```

### 3.3 消息格式

```json
{
  "id": "uuid-v4",
  "nick": "alice",
  "type": "msg",
  "body": "hello everyone",
  "ts": 1711036800.123
}
```

type 枚举：`msg`, `action` (/me), `join`, `leave`, `nick`

### 3.4 命令

|命令                          |描述                                                        |
|----------------------------|----------------------------------------------------------|
|`/zenoh join <#channel>`    |加入 channel，创建 buffer，subscribe 消息，声明 liveliness token     |
|`/zenoh join @<nick>`       |开启 private buffer，subscribe private 通道                     |
|`/zenoh leave [target]`     |离开当前或指定的 channel/private                                   |
|`/zenoh nick <n>`           |修改昵称，广播 nick 变更                                           |
|`/zenoh list`               |列出已加入的 channel 和 private                                   |
|`/zenoh status`             |显示 Zenoh session 状态（mode, routers, peers）                |
|`/zenoh send <target> <msg>`|程序化发送消息（供其他脚本调用）                                          |

### 3.5 对外暴露的 Signal（供其他脚本 hook）

```python
# 收到消息时
# buffer 字段格式: "channel:#general" 或 "private:@alice"
weechat.hook_signal_send("zenoh_message_received",
    weechat.WEECHAT_HOOK_SIGNAL_STRING,
    json.dumps({"buffer": buffer_label, "nick": nick, "body": body, "type": msg_type}))

# 在线状态变化时
weechat.hook_signal_send("zenoh_presence_changed",
    weechat.WEECHAT_HOOK_SIGNAL_STRING,
    json.dumps({"nick": nick, "online": True}))
```

### 3.6 核心实现

See `weechat-zenoh/weechat-zenoh.py`.

-----

## 4. 组件 2：weechat-channel-server

### 4.1 定位

Claude Code 的 Channel MCP server（Claude Code plugin 形式）。它是 Claude Code 的子进程，通过 stdio 与 Claude Code 通信（MCP 协议），通过 Zenoh pub/sub 与 WeeChat（或任何 Zenoh 节点）通信。**不知道 WeeChat 的存在**——它只知道 Zenoh topic 和 MCP 协议。

### 4.2 独立使用场景

用户安装 weechat-channel-server 插件后，**不需要 weechat-agent.py**，也能实现与 WeeChat 的通信：

```bash
# 安装插件
claude
/plugin install weechat-channel  # 从本地路径或 marketplace

# 启动 Claude Code with channel
claude --dangerously-load-development-channels plugin:weechat-channel

# 此时 agent0 已经在 Zenoh 网络上了
# 任何运行 weechat-zenoh 的 WeeChat 实例：
#   /zenoh join @agent0
# 即可与 Claude Code 对话
```

### 4.3 Zenoh Topic 约定

weechat-channel-server 使用与 weechat-zenoh 相同的 topic 约定：

```
订阅（接收消息）:
  wc/private/{pair}/messages          ← Private 消息（pair 包含 agent name）
  wc/channels/{channel}/messages      ← Channel 消息（如果 agent 被加入 channel）

发布（发送回复）:
  wc/private/{pair}/messages          → Private 回复
  wc/channels/{channel}/messages      → Channel 回复

在线状态:
  wc/presence/{agent_name}            → liveliness token
  wc/channels/{channel}/presence/{agent_name} → channel 内在线状态
```

**关键设计**：Agent 的回复走的是**和普通用户完全相同的 topic**。weechat-zenoh 收到消息后，不区分是人类发的还是 Agent 发的——只看 `nick` 字段。

### 4.4 文件结构

```
weechat-channel-server/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── pyproject.toml
├── server.py
├── tools.py
├── message.py
├── skills/
└── README.md
```

### 4.5 核心实现

See `weechat-channel-server/server.py`, `tools.py`, `message.py`.

-----

## 5. 组件 3：weechat-agent

### 5.1 定位

Claude Code Agent 生命周期管理脚本。它是 weechat-zenoh 的上层消费者，通过 WeeChat 命令和 signal 与 weechat-zenoh 交互。负责启动/停止 Claude Code 进程、管理 tmux pane。

### 5.2 与 weechat-zenoh 的交互方式

weechat-agent **不直接调用 Zenoh API**。它通过以下方式与 weechat-zenoh 协作：

```python
# 创建 private buffer → 执行 weechat-zenoh 命令
weechat.command("", "/zenoh join @agent0")

# 监听消息（检测 agent 的结构化命令输出）
weechat.hook_signal("zenoh_message_received", "on_msg_signal_cb", "")

# 发送消息给 agent
weechat.command("", "/zenoh send @agent0 hello")
```

### 5.3 命令

|命令                                      |描述                                        |
|----------------------------------------|------------------------------------------|
|`/agent create <n> [--workspace <path>]`|启动新 Claude Code 实例 + channel plugin       |
|`/agent stop <n>`                       |停止 Agent（不能停 agent0）                      |
|`/agent restart <n>`                    |重启 Agent                                  |
|`/agent list`                           |列出所有 Agent 及状态                            |
|`/agent join <agent> <#channel>`        |让 Agent 加入 channel                        |

### 5.4 核心实现

See `weechat-agent/weechat-agent.py`.

-----

## 6. 启动脚本

### 6.1 start.sh

See `start.sh`.

### 6.2 stop.sh

See `stop.sh`.

-----

## 7. 文件结构

```
weechat-claude/
├── start.sh
├── stop.sh
├── weechat-zenoh/
│   └── weechat-zenoh.py
├── weechat-agent/
│   └── weechat-agent.py
├── weechat-channel-server/
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── .mcp.json
│   ├── pyproject.toml
│   ├── server.py
│   ├── tools.py
│   ├── message.py
│   ├── skills/
│   └── README.md
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_message.py
│   │   ├── test_tools.py
│   │   ├── test_zenoh_protocol.py
│   │   └── test_agent_lifecycle.py
│   └── integration/
│       ├── test_zenoh_pubsub.py
│       ├── test_channel_bridge.py
│       └── test_private_and_channel.py
└── docs/
    └── PRD.md
```

-----

## 8. 端到端测试流程

### 8.1 环境准备

```bash
claude --version          # >= 2.1.80
uv --version              # >= 0.4
weechat --version         # >= 4.0
tmux -V
python3 -c "import zenoh" # eclipse-zenoh

git clone https://github.com/ezagent42/weechat-claude.git
cd weechat-claude
```

### 8.2 Test 1：weechat-zenoh 独立测试（人 ↔ 人）

```bash
# 终端 A
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick alice
/zenoh join #test

# 终端 B（同一 LAN）
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick bob
/zenoh join #test
```

### 8.3 Test 2：weechat-channel-server 独立测试

```bash
# 终端 A：Claude Code + channel plugin
claude --dangerously-load-development-channels plugin:weechat-channel

# 终端 B：WeeChat + weechat-zenoh
weechat
/python load weechat-zenoh.py
/zenoh nick alice
/zenoh join @agent0
# 输入: hello agent0
```

### 8.4 Test 3：完整系统启动

```bash
./start.sh ~/my-project alice
```

### 8.5–8.10

See original PRD for private, channel @mention, dynamic agent creation, agent lifecycle, and multi-user tests.

-----

## 9. 限制与约束

|约束                              |影响                                                       |Mitigation                                |
|--------------------------------|---------------------------------------------------------|------------------------------------------|
|Channel research preview        |自定义 channel 必须用 `--dangerously-load-development-channels`|等正式发布                                     |
|claude.ai 登录必需                  |不支持 API key                                              |使用 claude.ai 账号                           |
|`--dangerously-skip-permissions`|Claude 无需确认即可执行文件操作                                      |仅在信任环境使用                                  |
|zenohd 必须运行                    |所有 Zenoh 通信依赖本地 zenohd                                  |start.sh 自动启动                             |
|无跨 session 历史                   |重启后消息丢失                                                  |WeeChat logger 自动保存本地；未来可接入 zenohd storage|

-----

## 10. 未来演进

|方向                  |描述                                            |
|--------------------|----------------------------------------------|
|**Agent 间通信**       |Agent A publish 到 Agent B 的 private topic，直接协作 |
|**zenohd + storage**|zenohd 已作为基础设施就绪，接入 filesystem/rocksdb storage backend 即可提供跨 session 消息历史|
|**飞书桥接**            |复用 Zenoh 总线，飞书作为另一个 Zenoh 节点                  |
|**Ed25519 身份**      |消息签名验证，防冒充                                    |
|**Socialware**      |Channel → Slot，Agent role → Kit，Capability 权限 |
|**Web UI**          |WeeChat relay API 暴露 Web 前端                    |
