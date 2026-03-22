# 测试

## 测试架构

| 类型 | 目录 | 特点 |
|------|------|------|
| Unit | `tests/unit/` | Mock Zenoh session，快速，无外部依赖 |
| Integration | `tests/integration/` | 真实 Zenoh client session，需要 zenohd 在 localhost:7447 运行 |

## 运行测试

```bash
# 全部测试
pytest

# 仅 unit 测试（快速）
pytest tests/unit/

# 仅 integration 测试（需要 zenohd 在 localhost:7447 运行）
pytest -m integration tests/integration/

# 单个测试
pytest tests/unit/test_message.py::test_specific -v
```

## Fixture 说明

### Unit Test Fixture（`tests/conftest.py`）

`MockZenohSession` 提供：

- `put()` — 记录发布的消息到 `published` 列表
- `declare_publisher()` / `declare_subscriber()` — 返回 mock 对象
- `liveliness()` — 返回 mock liveliness 支持

使用方式：

```python
def test_something(mock_zenoh_session):
    # mock_zenoh_session 是 MockZenohSession 实例
    # 调用后检查 mock_zenoh_session.published
```

### Integration Test Fixture（`tests/integration/conftest.py`）

- `zenoh_session` — 单个 client 模式 Zenoh session（连接 `tcp/127.0.0.1:7447`）
- `zenoh_sessions` — 两个 session，用于测试 pub/sub 通信

前提：需要 zenohd 运行在 localhost:7447。

## 添加测试

### Unit Test

- 放在 `tests/unit/` 下
- 文件命名：`test_<模块名>.py`
- 使用 `mock_zenoh_session` fixture
- 异步测试自动支持（`asyncio_mode = auto`）

现有 unit test 文件：
- `test_message.py` — 消息工具（dedup、mention、chunking、topic）
- `test_tools.py` — MCP tool handler
- `test_zenoh_protocol.py` — Zenoh 消息协议
- `test_zenoh_signals.py` — WeeChat signal 格式
- `test_zenoh_config.py` — Zenoh client config 构造
- `test_zenoh_asyncio_bridge.py` — Zenoh 线程到 async 桥接
- `test_server.py` — server.py notification injection
- `test_agent_lifecycle.py` — Agent 生命周期和 pane 管理

### Integration Test

- 放在 `tests/integration/` 下
- 使用 `@pytest.mark.integration` 标记
- 使用 `zenoh_session` / `zenoh_sessions` fixture

## 手动测试指南

以下测试需要完整的 WeeChat + Claude Code + tmux 运行时，无法自动化。

### Phase 1：基础设施

1. **start.sh 依赖安装** — 运行 `./start.sh`，确认 `uv pip install --system` 被使用
2. **zenohd 启动** — 确认 zenohd 在 7447 端口运行

### Phase 2：weechat-zenoh

1. **`/me` action** — 输入 `/me waves`，确认对方收到 action 类型消息
2. **Nick 变更** — `/zenoh nick newname`，确认所有 channel 收到 nick 变更广播
3. **Private 警告** — 向不在线的用户发起 private，确认显示离线提示
4. **Status 增强** — `/zenoh status` 应显示 zid、peers、routers

### Phase 3：Channel Server

1. **Private 消息桥接** — 用户发消息给 agent0，确认 Claude Code 收到 MCP notification
2. **Channel @mention** — 在 channel 中 `@agent0 help`，确认 agent 只响应被 mention 的消息
3. **Presence** — agent join channel 后，确认 nicklist 显示 agent

### Phase 4：Agent 管理

1. **多 Agent pane** — `/agent create helper`，确认新 tmux pane 创建
2. **定向 stop** — `/agent stop helper`，确认只终止对应 pane
3. **Restart** — `/agent restart helper`，确认重启成功

### Phase 5：zenohd 生命周期

1. **共享 zenohd** — 多用户场景下确认 `./stop.sh` 不会误杀其他用户的 zenohd
