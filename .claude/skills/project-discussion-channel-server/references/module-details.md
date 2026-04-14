# Channel-Server Module Details

> 从 `.artifacts/bootstrap/module-reports/cs_*.json` 汇总生成（2026-04-14）。

## cs_server

**职责**：MCP server 桥接 IRC <-> Claude Code。通过 IRC reactor 守护线程接收消息，asyncio.Queue 桥接到 MCP async 循环，以 JSON-RPC notification 注入 Claude Code。(server.py:290 `main()`)

**关键接口**：

| 接口 | 位置 | 说明 |
|------|------|------|
| `inject_message(write_stream, msg, context)` | server.py:43 | 发送 MCP notification（method: notifications/claude/channel） |
| `poll_irc_queue(queue, write_stream)` | server.py:63 | Async 循环消费 IRC 消息队列并注入 Claude Code |
| `setup_irc(queue, loop)` | server.py:76 | 初始化 IRC reactor + 连接 + 事件注册，返回 (connection, joined_channels) |
| `_handle_sys_message(msg, sender_nick, conn, channels)` | server.py:186 | 分发 sys 消息：stop_request/join_request/status_request |
| `load_instructions(agent_name)` | server.py:212 | 加载 instructions.md 并插值 $agent_name |
| `create_server()` | server.py:219 | 创建 MCP Server 实例 (名称 'zchat-channel') |
| `register_tools(server, state)` | server.py:224 | 注册 MCP tools: reply + join_channel |
| `_handle_reply(connection, arguments)` | server.py:270 | reply tool 实现：chunk + privmsg |
| `_handle_join_channel(connection, arguments)` | server.py:280 | join_channel tool 实现 |
| `main()` | server.py:290 | Async 入口：queue + server + IRC + task_group |
| `entry_point()` | server.py:315 | 同步入口（console_scripts） |

**MCP Tools**：

| Tool | 参数 | 位置 | 说明 |
|------|------|------|------|
| `reply` | `chat_id: str, text: str` | server.py:236 | 向 IRC channel/user 发送消息（自动 chunk） |
| `join_channel` | `channel_name: str` | server.py:249 | 加入 IRC channel |

**IRC 事件处理器**（嵌套在 `setup_irc()` 内）：

| 事件 | 处理器 | 位置 | 说明 |
|------|--------|------|------|
| welcome | `on_welcome()` | server.py:97 | 自动 join IRC_CHANNELS 中的频道 |
| pubmsg | `on_pubmsg()` | server.py:112 | 检测 @mention，清理后入队 |
| privmsg | `on_privmsg()` | server.py:133 | 解码 sys 消息或作为普通消息入队 |
| disconnect | `on_disconnect()` | server.py:156 | 5s 后重连 |

**环境变量配置**：

| 变量 | 默认值 | 位置 | 说明 |
|------|--------|------|------|
| AGENT_NAME | agent0 | server.py:31 | IRC nick |
| IRC_SERVER | 127.0.0.1 | server.py:32 | IRC 服务器地址 |
| IRC_PORT | 6667 | server.py:33 | IRC 端口 |
| IRC_CHANNELS | general | server.py:34 | 逗号分隔的频道列表 |
| IRC_TLS | false | server.py:35 | 是否启用 TLS |

**Slash 命令**（commands/ 目录）：

| 命令 | 文件 | 说明 |
|------|------|------|
| /zchat:reply | commands/reply.md | 回复 channel/user，解析 --channel/-c 和 --text/-t |
| /zchat:dm | commands/dm.md | 私信用户，解析 --user/-u 和 --text/-t |
| /zchat:join | commands/join.md | 加入 channel，解析 --channel/-c |
| /zchat:broadcast | commands/broadcast.md | 广播到所有已加入 channel，解析 --text/-t 和可选 --channels/-C |

**依赖关系**：
- -> `message.py`（detect_mention, clean_mention, chunk_message）
- -> `zchat-protocol`（decode_sys_from_irc, make_sys_message, encode_sys_for_irc）
- -> `mcp[cli]`（Server, stdio_server, JSONRPCNotification, TextContent）
- -> `irc`（irc.client.Reactor）
- -> `instructions.md`（agent 指令模板，string.Template 插值）

**测试覆盖**：

| 测试文件 | 测试数 | 覆盖内容 |
|---------|--------|---------|
| tests/unit/test_legacy.py | 5 | sys message roundtrip, 非 sys 文本过滤, instructions 插值 ($agent_name), routing rules 存在, soul.md 引用 |

---

## cs_message

**职责**：IRC 消息处理纯工具模块。提供 @mention 检测/清理和消息分 chunk 能力，确保消息符合 IRC 512 字节限制。(message.py)

**关键接口**：

| 接口 | 位置 | 说明 |
|------|------|------|
| `detect_mention(body, agent_name) -> bool` | message.py:12 | 检测 @agent_name 子串 |
| `clean_mention(body, agent_name) -> str` | message.py:17 | 移除 @agent_name 并 strip |
| `chunk_message(text, max_bytes=390) -> list[str]` | message.py:27 | UTF-8 字节安全分片，CJK 兼容 |
| `_sanitize_for_irc(text) -> str` | message.py:22 | 换行替换为空格（IRC 单行协议） |
| `MAX_MESSAGE_BYTES` | message.py:9 | 常量 390（512 - ~120 IRC header） |

**依赖关系**：
- 无外部依赖（纯 Python 标准库）

**测试覆盖**：

| 测试文件 | 测试数 | 覆盖内容 |
|---------|--------|---------|
| tests/unit/test_message.py | 7 | mention 检测, mention 清理, 短消息单 chunk, 长 ASCII 分 chunk, CJK 分 chunk, 换行清理, dash 分隔符兼容 |

---

## 模块依赖图

```
┌─────────────┐     ┌──────────────┐
│ cs_server   │────>│ cs_message   │
│ (server.py) │     │ (message.py) │
└──────┬──────┘     └──────────────┘
       │
       ├──> zchat-protocol (sys messages)
       ├──> mcp[cli] (MCP server framework)
       ├──> irc (IRC client reactor)
       └──> instructions.md (agent template)
```
