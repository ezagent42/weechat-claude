# weechat-zenoh 开发文档

## 定位

WeeChat 的 Zenoh P2P 聊天基础设施。提供 channel/private 管理、消息收发、在线状态追踪。**不知道 Claude Code 的存在**——任何 Zenoh 节点（人类、Agent、bot）对它而言都是平等的 participant。

## 文件结构

```
weechat-zenoh/
├── weechat-zenoh.py    # 主插件（WeeChat 加载入口）
└── helpers.py          # 纯函数工具集（可独立测试）
```

## 核心模块

### weechat-zenoh.py

| 函数 | 职责 |
|------|------|
| `zc_init()` | 初始化 Zenoh session、设置 nick、声明全局 liveliness token、注册 poll timer |
| `zc_deinit()` | 清理所有 token/subscriber/publisher，关闭 session |
| `join_channel(channel_id)` | 创建 buffer、订阅消息、声明 liveliness 和 presence 监控 |
| `join_private(target_nick)` | 创建 private buffer（pair 按字母序排列） |
| `leave_channel()` / `leave_private()` | 通过 `_cleanup_key()` 清理资源 |
| `_publish_event(pub_key, msg_type, body)` | 序列化消息为 JSON，通过 Zenoh pub 发送 |
| `buffer_input_cb()` | 用户输入回调——解析 `/me`、发布消息、发送 signal |
| `_on_channel_msg()` / `_on_private_msg()` | Zenoh 消息回调 → 入队到 `msg_queue` |
| `_on_channel_presence()` | Zenoh liveliness 回调 → 入队到 `presence_queue` |
| `poll_queues_cb()` | 50ms timer 回调——出队、渲染到 buffer、发送 signal |
| `zenoh_cmd_cb()` | `/zenoh` 命令分发器 |

### helpers.py

| 函数 | 职责 |
|------|------|
| `build_zenoh_config(connect)` | 构造 Zenoh client config（默认连接 `tcp/127.0.0.1:7447`） |
| `target_to_buffer_label(target, my_nick)` | 内部 key → WeeChat buffer label 转换 |
| `parse_input(input_data)` | 检测 `/me` 前缀，返回 `(msg_type, body)` |

## 扩展点

**添加新命令**：在 `zenoh_cmd_cb()` 的分发逻辑中添加分支。

**监听消息事件**：其他 WeeChat 插件可以 hook signal：

```python
weechat.hook_signal("zenoh_message_received", "my_callback", "")
weechat.hook_signal("zenoh_presence_changed", "my_callback", "")
```

Signal 的 payload 是 JSON string，格式见 [架构与协议](architecture.md#signal-约定)。

## 注意事项

- **WeeChat callback 不能阻塞** — Zenoh 回调运行在 Zenoh 线程中，不能直接调用 WeeChat API。必须通过 deque 入队，由 timer callback (`poll_queues_cb`) 在 WeeChat 主线程中出队处理。
- **50ms poll 间隔** — 消息延迟上限 50ms，在此频率下 CPU 开销极低。
- **Nick 变更广播** — `/zenoh nick` 会向所有已加入的 channel 发布 `nick` 类型事件，并重新声明所有 liveliness token。
