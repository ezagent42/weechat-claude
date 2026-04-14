# Phase 4: Transport + Server 重构 + E2E 测试

> **Submodule 分支:** `feat/server-v1`
> **仓库:** zchat-channel-server submodule
> **Spec 参考:** `spec/channel-server/02-channel-server.md` §4 MCP Tools + §6 IRC Transport + §7 启动流程
> **预估:** 3-4h
> **依赖:** Phase 2 (engine/) + Phase 3 (bridge_api/) 都已 merge
> **不可并行:** 这是集成阶段

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
代码开发在 `zchat-channel-server/` submodule 内。

```bash
cd zchat-channel-server

# Phase 2+3 merge 后，基于合并结果创建分支
git checkout -b feat/server-v1

# 验证 Phase 1+2+3 全部完成
uv run python -c "
from protocol.gate import gate_message
from engine.conversation_manager import ConversationManager
from bridge_api.ws_server import BridgeAPIServer
print('All modules OK')
"

mkdir -p transport
```

**依赖:** Phase 2 (engine/) + Phase 3 (bridge_api/) 都必须已 merge 到当前分支。

---

## Dev-loop 闭环（6 步 → e2e-report 结束）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc → .artifacts/eval-docs/cs-eval-server.md
/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "IRC Transport 提取 + server.py v1.0 集成重构"

# Step 2: test-plan → .artifacts/test-plans/cs-plan-server.md (包含 unit + E2E)
/dev-loop-skills:skill-2-test-plan-generator

# Step 3: test-code → submodule 内 tests/unit/ + tests/e2e/
/dev-loop-skills:skill-3-test-code-writer

# Step 4: TDD 实现 → 注册 .artifacts/code-diffs/cs-diff-server.md
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-server

# Step 5: test-run → .artifacts/e2e-reports/cs-report-server.md (unit + E2E 两层)
/dev-loop-skills:skill-4-test-runner

# Step 6: 链条验证
/dev-loop-skills:skill-6-artifact-registry
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-server.md` 存在，unit + E2E 全 PASS 无 skip。

---

## 文件清单

| 源文件 | 测试文件 | 操作 | 内容 |
|--------|---------|------|------|
| `transport/__init__.py` | — | 新建 | 包声明 |
| `transport/irc_transport.py` | `tests/unit/test_irc_transport.py` | 新建（从 server.py 提取） | IRC 连接管理 |
| `server.py` | — | **改造** | 胶水代码：初始化 + 启动 |
| — | `tests/e2e/conftest.py` | 新建 | E2E fixtures |
| — | `tests/e2e/test_conversation_lifecycle.py` | 新建 | 对话全生命周期 |
| — | `tests/e2e/test_mode_switching.py` | 新建 | 模式切换全流程 |
| — | `tests/e2e/test_gate_enforcement.py` | 新建 | Gate 拦截验证 |
| — | `tests/e2e/test_bridge_api_e2e.py` | 新建 | Bridge 连接验证 |

---

## Task 4.1: transport/irc_transport.py

**从现有 server.py L76-180 提取 setup_irc() 到独立模块**

- [ ] **写测试** `tests/unit/test_irc_transport.py`（mock IRC 连接）

```python
import pytest
from unittest.mock import MagicMock, patch
from transport.irc_transport import IRCTransport

def test_irc_transport_init():
    t = IRCTransport(server="127.0.0.1", port=6667, nick="test-agent")
    assert t.nick == "test-agent"
    assert t.joined_channels == set()

def test_channel_naming():
    t = IRCTransport(server="127.0.0.1", port=6667, nick="test")
    assert t.conv_channel_name("feishu_oc_abc") == "#conv-feishu_oc_abc"

def test_extract_conv_id():
    t = IRCTransport(server="127.0.0.1", port=6667, nick="test")
    assert t.extract_conv_id("#conv-feishu_oc_abc") == "feishu_oc_abc"
    assert t.extract_conv_id("#admin") is None  # 非对话频道
```

- [ ] **实现 transport/irc_transport.py** — 从 server.py 移动 IRC 相关代码
- [ ] **验证现有 12 个 unit 测试仍然通过**（无回归）
- [ ] **Commit**

---

## Task 4.2: server.py 重构

**改造 server.py：从 260 行单文件 → 集成所有模块的胶水代码**

- [ ] **Step 1: 新增 engine 初始化**

```python
# server.py main() 中新增:
from engine.event_bus import EventBus
from engine.conversation_manager import ConversationManager
from engine.mode_manager import ModeManager
from engine.timer_manager import TimerManager
from engine.participant_registry import ParticipantRegistry
from bridge_api.ws_server import BridgeAPIServer
from transport.irc_transport import IRCTransport

async def main():
    # ... 现有 MCP 初始化保留 ...
    
    db_path = os.environ.get("CS_DB_PATH", "conversations.db")
    event_bus = EventBus(db_path.replace(".db", "_events.db"))
    conv_manager = ConversationManager(db_path)
    mode_manager = ModeManager(event_bus)
    timer_manager = TimerManager(event_bus)
    registry = ParticipantRegistry()
    bridge_server = BridgeAPIServer(
        conversation_manager=conv_manager,
        mode_manager=mode_manager,
        event_bus=event_bus,
        port=int(os.environ.get("BRIDGE_PORT", "9999"))
    )
```

- [ ] **Step 2: 改造 on_pubmsg**

```python
def on_pubmsg(conn, event):
    nick = event.source.nick
    channel = event.target
    body = event.arguments[0]
    
    participant = registry.identify(nick)
    if participant is None:
        return
    
    # 命令处理
    if body.startswith("/"):
        conv_id = irc_transport.extract_conv_id(channel)
        if conv_id:
            cmd = parse_command(body)
            # 执行命令...
        return
    
    # 对话消息处理
    conv_id = irc_transport.extract_conv_id(channel)
    if not conv_id:
        return
    conversation = conv_manager.get(conv_id)
    if not conversation:
        return
    
    msg = Message(id=os.urandom(4).hex(), source=participant.id,
                  conversation_id=conv_id, content=body)
    msg = gate_engine.process(conversation, participant, msg)
    message_store.save(msg)
    
    # 分发
    if msg.visibility in (MessageVisibility.PUBLIC, MessageVisibility.SIDE):
        await bridge_server.send_to_bridges(conv_id, {...}, msg.visibility.value)
    if msg.visibility != MessageVisibility.SYSTEM:
        loop.call_soon_threadsafe(queue.put_nowait, (msg_dict, conv_id))
```

- [ ] **Step 3: 新增 MCP tools**

```python
# register_tools 中新增:
Tool(name="edit_message", description="Edit a sent message", inputSchema={...})
Tool(name="join_conversation", description="Join a conversation", inputSchema={...})
Tool(name="send_side_message", description="Send side channel message", inputSchema={...})
Tool(name="list_conversations", description="List active conversations", inputSchema={...})
Tool(name="get_conversation_status", description="Get conversation details", inputSchema={...})
```

- [ ] **Step 4: 新增 App tools 注册**（参考 spec §4 App MCP Tools）
- [ ] **Step 5: 验证现有测试无回归**
- [ ] **Commit**

---

## Task 4.3: E2E 测试

- [ ] **创建 E2E conftest**

```python
# tests/e2e/conftest.py
import os, subprocess, time, asyncio, json
import pytest
import websockets

@pytest.fixture(scope="session")
def e2e_port():
    return 16667 + (os.getpid() % 1000)

@pytest.fixture(scope="session")
def bridge_port():
    return 19999 + (os.getpid() % 1000)

@pytest.fixture(scope="session")
def ergo_server(e2e_port, tmp_path_factory):
    """启动 ergo IRC server"""
    work = tmp_path_factory.mktemp("ergo")
    # 生成 ergo 配置...
    proc = subprocess.Popen(["ergo", "run", "--conf", str(work / "ergo.yaml")])
    time.sleep(2)
    yield proc
    proc.terminate()

@pytest.fixture(scope="session")
def channel_server(ergo_server, e2e_port, bridge_port, tmp_path_factory):
    """启动 channel-server"""
    proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "server"],
        env={**os.environ,
             "IRC_SERVER": "127.0.0.1", "IRC_PORT": str(e2e_port),
             "BRIDGE_PORT": str(bridge_port), "AGENT_NAME": "e2e-agent"}
    )
    time.sleep(3)
    yield proc
    proc.terminate()

@pytest.fixture
async def bridge_ws(bridge_port):
    ws = await websockets.connect(f"ws://localhost:{bridge_port}")
    await ws.send(json.dumps({
        "type": "register", "bridge_type": "test",
        "instance_id": "e2e-test", "capabilities": ["customer", "operator", "admin"]
    }))
    resp = json.loads(await ws.recv())
    assert resp["type"] == "registered"
    yield ws
    await ws.close()
```

- [ ] **写 E2E 测试**

```python
# tests/e2e/test_conversation_lifecycle.py
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_customer_connect_creates_conversation(channel_server, bridge_ws):
    await bridge_ws.send(json.dumps({
        "type": "customer_connect",
        "conversation_id": "e2e_test_001",
        "customer": {"id": "david", "name": "David"}
    }))
    # 发消息
    await bridge_ws.send(json.dumps({
        "type": "customer_message",
        "conversation_id": "e2e_test_001",
        "text": "hello", "message_id": "msg_001"
    }))
    # 等待 agent 回复（或至少确认消息被处理）
    # ...

# tests/e2e/test_mode_switching.py
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_operator_join_triggers_copilot(channel_server, bridge_ws):
    # 创建对话
    await bridge_ws.send(json.dumps({
        "type": "customer_connect", "conversation_id": "e2e_mode_001",
        "customer": {"id": "david", "name": "David"}
    }))
    # Operator 加入
    await bridge_ws.send(json.dumps({
        "type": "operator_join", "conversation_id": "e2e_mode_001",
        "operator": {"id": "xiaoli", "name": "小李"}
    }))
    # 验证 mode.changed 事件
    event = json.loads(await asyncio.wait_for(bridge_ws.recv(), timeout=5))
    assert event.get("event_type") == "mode.changed"
    assert event["data"]["to"] == "copilot"

# tests/e2e/test_gate_enforcement.py
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_takeover_blocks_agent_public(channel_server, bridge_ws):
    # 创建对话 + operator 加入 + /hijack
    # 验证 agent 的 public 消息被降级为 side（customer bridge 收不到）
    pass
```

- [ ] **运行 E2E**

```bash
uv run pytest tests/e2e/ -v -m e2e --timeout=30
```

- [ ] **Commit + Merge**

---

## 完成标准

- [ ] `transport/irc_transport.py` 存在，IRC 逻辑从 server.py 提取
- [ ] `server.py` 集成所有模块，新增 5 个 MCP tools
- [ ] 现有 12 个 unit 测试无回归
- [ ] 4 个 E2E 测试 PASS
- [ ] commit 完成（由人类操作 merge）
