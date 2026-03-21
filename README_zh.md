# WeeChat-Claude

**[English](README.md)** | **[中文](README_zh.md)**

基于本地/局域网的多 Agent 协作系统，通过 [Zenoh](https://zenoh.io/) P2P 消息总线连接 [WeeChat](https://weechat.org/) 与 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)。

在终端里运行多个 Claude Code 实例作为聊天参与者——与它们对话、让它们互相协作、统一管理生命周期。

## 架构

三个可组合的独立组件，通过 Zenoh topic 约定通信。每个组件均可独立使用：

```
场景 1：人 ↔ 人（仅需 weechat-zenoh）
┌─────────┐  Zenoh  ┌─────────┐
│ WeeChat │ ◄─────► │ WeeChat │
│ + zenoh │         │ + zenoh │
│ (Alice) │         │ (Bob)   │
└─────────┘         └─────────┘

场景 2：人 ↔ Agent（+ weechat-channel-server）
┌─────────┐  Zenoh  ┌───────────────────┐
│ WeeChat │ ◄─────► │ weechat-channel   │
│ + zenoh │         │ (MCP server)      │
│ (Alice) │         │    ↕ stdio        │
└─────────┘         │ Claude Code       │
                    └───────────────────┘

场景 3：完整部署（三个组件全装）
┌─────────────────────────────────┐
│ WeeChat                         │
│  weechat-zenoh.py   (P2P 通信)   │
│  weechat-agent.py   (生命周期管理) │
└────────┬────────────────┬───────┘
         │  Zenoh mesh    │ subprocess
    ┌────▼────┐      ┌───▼──────────┐
    │ WeeChat │      │ Claude Code  │
    │ (Bob)   │      │ + channel    │
    └─────────┘      │ (agent0)     │
                     └──────────────┘
```

| 组件 | 类型 | 用途 |
|------|------|------|
| **weechat-zenoh** | WeeChat Python 插件 | 基于 Zenoh 的 P2P channel 和 private buffer。平等对待所有参与者，不感知 Claude 的存在。 |
| **weechat-channel-server** | Claude Code 插件 (MCP server) | 连接 Claude Code 与 Zenoh。不感知 WeeChat 的存在，只知道 Zenoh topic 和 MCP 协议。 |
| **weechat-agent** | WeeChat Python 插件 | Agent 生命周期管理器。在 tmux pane 中启动/停止 Claude Code 实例。 |

## 前置依赖

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) ≥ 2.1.80
- [uv](https://docs.astral.sh/uv/) ≥ 0.4
- [WeeChat](https://weechat.org/) ≥ 4.0
- [tmux](https://github.com/tmux/tmux)
- Python ≥ 3.10

## 快速开始

```bash
git clone https://github.com/ezagent42/weechat-claude.git
cd weechat-claude

# 启动完整系统（agent0 + WeeChat，运行在 tmux 中）
./start.sh ~/my-project alice
```

启动脚本会自动完成：
1. 安装依赖（eclipse-zenoh、MCP server 依赖）
2. 将 WeeChat 插件复制到配置目录
3. 创建 tmux session，包含两个 pane：
   - **Pane 0**：Claude Code (agent0) + channel 插件
   - **Pane 1**：WeeChat + zenoh/agent 插件

启动后，在 WeeChat 中与 agent 私聊：

```
/zenoh join @agent0
你好 agent0，你能帮我做什么？
```

## 使用方法

### WeeChat 命令

**聊天命令 (weechat-zenoh)**

| 命令 | 说明 |
|------|------|
| `/zenoh join #channel` | 加入 channel |
| `/zenoh join @nick` | 开启 private buffer |
| `/zenoh leave [target]` | 离开当前或指定的 channel/private |
| `/zenoh nick <name>` | 修改昵称 |
| `/zenoh list` | 列出已加入的 channel 和 private |
| `/zenoh status` | 显示 Zenoh session 状态 |

**Agent 管理命令 (weechat-agent)**

| 命令 | 说明 |
|------|------|
| `/agent create <name> [--workspace <path>]` | 创建新 Claude Code 实例 |
| `/agent stop <name>` | 停止 agent（不能停止 agent0） |
| `/agent restart <name>` | 重启 agent |
| `/agent list` | 列出所有 agent 及其状态 |
| `/agent join <agent> #channel` | 让 agent 加入 channel |

### 独立使用各组件

**人与人聊天**（仅需 weechat-zenoh）：

```bash
# 终端 A
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick alice
/zenoh join #team

# 终端 B（同一局域网）
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick bob
/zenoh join #team
```

**单 agent 模式（无需 agent 管理器）**（weechat-zenoh + weechat-channel-server）：

```bash
# 终端 A：启动 Claude Code + channel 插件
cd weechat-channel-server
claude --dangerously-load-development-channels plugin:weechat-channel

# 终端 B：WeeChat
weechat
/python load /path/to/weechat-zenoh.py
/zenoh nick alice
/zenoh join @agent0
```

## 消息协议

所有消息通过 Zenoh pub/sub 以 JSON 格式传输：

```json
{
  "id": "uuid-v4",
  "nick": "alice",
  "type": "msg",
  "body": "大家好",
  "ts": 1711036800.123
}
```

**消息类型**：`msg`（普通消息）、`action`（/me 动作）、`join`（加入）、`leave`（离开）、`nick`（改名）

**Zenoh topic 层级**：

```
wc/
├── channels/{channel_id}/
│   ├── messages                # Channel 消息 (pub/sub)
│   └── presence/{nick}         # 成员在线状态 (liveliness)
├── private/{sorted_pair}/
│   └── messages                # Private 消息（按字母序排列，如 alice_bob）
└── presence/{nick}             # 全局在线状态 (liveliness)
```

## 项目结构

```
weechat-claude/
├── start.sh                        # 系统启动脚本
├── stop.sh                         # 停止 tmux session
├── weechat-zenoh/
│   └── weechat-zenoh.py            # P2P 聊天插件
├── weechat-agent/
│   └── weechat-agent.py            # Agent 生命周期管理插件
├── weechat-channel-server/
│   ├── server.py                   # MCP server + Zenoh 桥接
│   ├── tools.py                    # MCP 工具（reply）
│   ├── message.py                  # 消息工具（去重、分块、@提及检测）
│   ├── pyproject.toml              # 依赖声明
│   └── .claude-plugin/plugin.json  # Claude Code 插件元数据
├── tests/
│   ├── conftest.py                 # Mock Zenoh fixtures
│   ├── unit/                       # 单元测试（Mock，快速）
│   └── integration/                # 集成测试（真实 Zenoh peer）
└── docs/
    └── PRD.md                      # 完整设计文档
```

## 测试

```bash
# 单元测试（Mock Zenoh，快速）
pytest tests/unit/

# 集成测试（需要 Zenoh peer，较慢）
pytest -m integration tests/integration/

# 全部测试
pytest
```

## 已知限制

| 限制 | 影响 | 应对方案 |
|------|------|----------|
| Channel MCP 处于 research preview | 需要 `--dangerously-load-development-channels` 标志 | 等待正式发布 |
| Claude Code 需要登录 | 不支持 API key 认证 | 使用 claude.ai 账号 |
| `--dangerously-skip-permissions` | Claude 无需确认即可执行文件操作 | 仅在受信任环境中使用 |
| Zenoh Python + WeeChat .so | 部分系统上可能存在动态库冲突 | 计划中：Zenoh sidecar 进程 |
| 无跨 session 历史记录 | 重启后消息丢失 | WeeChat logger 自动保存本地；未来接入 zenohd storage |

## 路线图

- **Agent 间通信** — agent 之间通过 private topic 直接协作
- **zenohd + 存储后端** — 跨 session 的持久化消息历史
- **飞书桥接** — 飞书作为 Zenoh 网络中的另一个节点
- **Ed25519 签名** — 消息真实性验证，防止冒充
- **Web UI** — 通过 WeeChat relay API 提供 Web 前端

## 许可证

MIT
