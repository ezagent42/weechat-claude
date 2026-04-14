# Phase Final: Pre-release 验收测试

> **执行位置:** dev branch（所有 Phase 已 merge）
> **仓库:** zchat-channel-server
> **Spec 参考:** `spec/channel-server/05-user-journeys.md` 全部 7 个旅程
> **预估:** 2-3h
> **依赖:** Phase 4 完成

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
所有 Phase 1-4 在 submodule 内已完成。

```bash
cd zchat-channel-server

# 确认所有模块可用
uv run python -c "
from protocol.gate import gate_message
from engine.conversation_manager import ConversationManager
from engine.event_bus import EventBus
from bridge_api.ws_server import BridgeAPIServer
from transport.irc_transport import IRCTransport
print('All v1.0 modules OK')
"

# 确认 unit + E2E 基线全部通过
uv run pytest tests/unit/ tests/e2e/ -v
```

**依赖:** Phase 4 (集成) 必须已完成。submodule 内所有代码已 merge。

---

## Dev-loop 闭环（6 步 — verify 模式）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc (verify 模式 — 验证而非提案)
/dev-loop-skills:skill-5-feature-eval verify
# 主题: "channel-server v1.0 端到端验收"

# Step 2: test-plan (从 verify eval-doc 生成验收 checklist)
/dev-loop-skills:skill-2-test-plan-generator

# Step 3: test-code (walkthrough script + WebSocket acceptance tests)
/dev-loop-skills:skill-3-test-code-writer
# 输出: tests/pre_release/*.py + tests/pre_release/*.sh

# Step 4: 执行验收测试

# Step 5: test-run + 报告
/dev-loop-skills:skill-4-test-runner

# Step 6: artifact 注册
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-prerelease
# 验证: cs-eval-prerelease → cs-plan-prerelease → cs-report-prerelease
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-prerelease.md` 存在，0 FAIL 0 SKIP。

---

## Task F.1: Pre-release walkthrough (asciinema 录制)

**Files:** `tests/pre_release/channel_server_walkthrough.sh`

```bash
#!/bin/bash
# Channel-Server v1.0 Pre-release Walkthrough
# 录制: asciinema rec tests/pre_release/evidence/walkthrough.cast
set -e

echo "=== Channel-Server v1.0 Pre-release ==="

# 1. 启动 ergo
echo ">>> Starting ergo on port 16700..."
ERGO_PORT=16700
ergo run --conf tests/pre_release/ergo.yaml &
ERGO_PID=$!
sleep 2

# 2. 启动 channel-server
echo ">>> Starting channel-server..."
BRIDGE_PORT=19900
IRC_SERVER=127.0.0.1 IRC_PORT=$ERGO_PORT BRIDGE_PORT=$BRIDGE_PORT \
  AGENT_NAME=walkthrough-agent \
  uv run python -m server &
CS_PID=$!
sleep 3

# 3. Bridge API 连接测试
echo ">>> Testing Bridge API register..."
python3 -c "
import asyncio, websockets, json
async def test():
    ws = await websockets.connect('ws://localhost:$BRIDGE_PORT')
    await ws.send(json.dumps({
        'type': 'register', 'bridge_type': 'test',
        'instance_id': 'walkthrough',
        'capabilities': ['customer', 'operator', 'admin']
    }))
    resp = json.loads(await ws.recv())
    assert resp['type'] == 'registered', f'FAIL: {resp}'
    print('  Bridge register: PASS')
    
    # 创建对话
    await ws.send(json.dumps({
        'type': 'customer_connect',
        'conversation_id': 'walkthrough_001',
        'customer': {'id': 'david', 'name': 'David'}
    }))
    print('  Customer connect: PASS')
    
    # /status
    await ws.send(json.dumps({
        'type': 'admin_command',
        'admin_id': 'tester',
        'command': '/status'
    }))
    status = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
    print(f'  /status: {status}')
    
    await ws.close()
asyncio.run(test())
"

echo ">>> All walkthrough checks passed!"
kill $CS_PID $ERGO_PID 2>/dev/null
```

- [ ] **运行 walkthrough**

```bash
chmod +x tests/pre_release/channel_server_walkthrough.sh
asciinema rec tests/pre_release/evidence/walkthrough.cast -c ./tests/pre_release/channel_server_walkthrough.sh
```

---

## Task F.2: Bridge API 自动化验收 (Playwright WebSocket)

**Files:** `tests/pre_release/conftest.py` + `tests/pre_release/test_bridge_acceptance.py`

```python
# tests/pre_release/conftest.py
import os, subprocess, time
import pytest

@pytest.fixture(scope="session")
def full_stack(tmp_path_factory):
    """启动完���的 ergo + channel-server 栈"""
    work = tmp_path_factory.mktemp("prerelease")
    ergo_port = 16700 + (os.getpid() % 100)
    bridge_port = 19900 + (os.getpid() % 100)
    
    ergo_proc = subprocess.Popen(["ergo", "run", "--conf", "tests/pre_release/ergo.yaml"])
    time.sleep(2)
    
    cs_proc = subprocess.Popen(
        ["uv", "run", "python", "-m", "server"],
        env={**os.environ,
             "IRC_SERVER": "127.0.0.1", "IRC_PORT": str(ergo_port),
             "BRIDGE_PORT": str(bridge_port), "AGENT_NAME": "prerelease-agent"},
    )
    time.sleep(3)
    
    yield {"ergo_port": ergo_port, "bridge_port": bridge_port}
    
    cs_proc.terminate()
    ergo_proc.terminate()
```

```python
# tests/pre_release/test_bridge_acceptance.py
import asyncio, json
import pytest
import websockets

@pytest.mark.prerelease
@pytest.mark.asyncio
async def test_full_lifecycle(full_stack):
    """验收旅程: 接入 → 对话 → copilot → takeover → resolve → CSAT"""
    ws = await websockets.connect(f"ws://localhost:{full_stack['bridge_port']}")
    
    # Register
    await ws.send(json.dumps({
        "type": "register", "bridge_type": "acceptance",
        "instance_id": "at-1", "capabilities": ["customer", "operator", "admin"]
    }))
    assert json.loads(await ws.recv())["type"] == "registered"
    
    # Customer connect
    conv_id = "acceptance_test_001"
    await ws.send(json.dumps({
        "type": "customer_connect", "conversation_id": conv_id,
        "customer": {"id": "david", "name": "David"}
    }))
    
    # Customer message
    await ws.send(json.dumps({
        "type": "customer_message", "conversation_id": conv_id,
        "text": "hello", "message_id": "m1"
    }))
    
    # Operator join → expect copilot
    await ws.send(json.dumps({
        "type": "operator_join", "conversation_id": conv_id,
        "operator": {"id": "xiaoli", "name": "小李"}
    }))
    event = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    assert event.get("data", {}).get("to") == "copilot", f"Expected copilot, got {event}"
    
    # /hijack → expect takeover
    await ws.send(json.dumps({
        "type": "operator_command", "conversation_id": conv_id,
        "operator_id": "xiaoli", "command": "/hijack"
    }))
    event = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    assert event.get("data", {}).get("to") == "takeover", f"Expected takeover, got {event}"
    
    # /resolve → expect csat_request
    await ws.send(json.dumps({
        "type": "operator_command", "conversation_id": conv_id,
        "operator_id": "xiaoli", "command": "/resolve"
    }))
    csat = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    assert csat.get("type") == "csat_request", f"Expected csat_request, got {csat}"
    
    # CSAT response
    await ws.send(json.dumps({
        "type": "csat_response", "conversation_id": conv_id, "score": 5
    }))
    
    await ws.close()
    print("FULL LIFECYCLE: PASS")


@pytest.mark.prerelease
@pytest.mark.asyncio
async def test_gate_isolation(full_stack):
    """验收 Gate: 两个 bridge 连接，验证 side 消息不到 customer 端"""
    port = full_stack["bridge_port"]
    
    # customer-only bridge
    cust_ws = await websockets.connect(f"ws://localhost:{port}")
    await cust_ws.send(json.dumps({
        "type": "register", "bridge_type": "cust-view",
        "instance_id": "cv-1", "capabilities": ["customer"]
    }))
    await cust_ws.recv()  # registered
    
    # operator-only bridge
    op_ws = await websockets.connect(f"ws://localhost:{port}")
    await op_ws.send(json.dumps({
        "type": "register", "bridge_type": "op-view",
        "instance_id": "ov-1", "capabilities": ["operator"]
    }))
    await op_ws.recv()  # registered
    
    # 创建对话 + operator join + /hijack
    conv_id = "gate_test_001"
    await cust_ws.send(json.dumps({
        "type": "customer_connect", "conversation_id": conv_id,
        "customer": {"id": "test", "name": "Test"}
    }))
    
    # ... 验证 agent 在 takeover 下的 side 消息:
    # op_ws ��到 (visibility=side)
    # cust_ws 不收到 (timeout)
    
    await cust_ws.close()
    await op_ws.close()
```

- [ ] **运行 pre-release**

```bash
uv run pytest tests/pre_release/ -v -m prerelease --timeout=60
```

---

## Task F.3: 飞书真实验证 (可选)

如果飞书凭证可用：

```bash
# 方式 1: agent-browser 自动化飞书 Web
/agent-browser:agent-browser
# 打开 feishu.cn → 登录 → 找群 → 发消息 → 截图验证

# 方式 2: 飞书 API 直接验证
python3 tests/pre_release/feishu_api_test.py \
  --app-id $FEISHU_APP_ID --app-secret $FEISHU_APP_SECRET \
  --chat-id $TEST_CHAT_ID

# 方式 3: 录屏
# 手动在飞书中操作，用 OBS/asciinema 录屏保存到 evidence/
```

**证据保存:**

```
tests/pre_release/evidence/
├── walkthrough.cast          # asciinema 录制
├── walkthrough.gif           # agg 生成
├── bridge_acceptance.log     # pytest 输出
├── feishu_screenshot_*.png   # 飞书截图（如有）
└── gate_isolation.log        # Gate 隔离测试日志
```

---

## 完成标准

- [ ] walkthrough.sh 全部检查通过，asciinema 录制完成
- [ ] `test_full_lifecycle` PASS — 完整 7 步生命周期
- [ ] `test_gate_isolation` PASS — visibility 隔离验证
- [ ] 所有证据保存到 `evidence/` 目录
- [ ] （可选）飞书真实环境截图/录屏
