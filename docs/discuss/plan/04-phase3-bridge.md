# Phase 3: Bridge API 模块

> **Submodule 分支:** `feat/bridge-api`
> **仓库:** zchat-channel-server submodule
> **Spec 参考:** `spec/channel-server/02-channel-server.md` §5 Bridge API + `03-bridge-layer.md`
> **预估:** 1-2h
> **依���:** Phase 1 (protocol/) 已 merge
> **可并行:** 与 Phase 2 (engine/) 并行

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
代码开发在 `zchat-channel-server/` submodule 内。

```bash
cd zchat-channel-server

# 基于 Phase 1 完成的分支创建新分支
git checkout feat/protocol
git checkout -b feat/bridge-api

# 验证 Phase 1 (protocol/) 已完成
uv run python -c "from protocol.gate import gate_message; import websockets; print('OK')"

mkdir -p bridge_api
```

**依赖:** Phase 1 (protocol/) 必须已完成。可与 Phase 2 (engine/) 并行。

---

## Dev-loop 闭环（6 步 → e2e-report 结束）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc → .artifacts/eval-docs/cs-eval-bridge.md
/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "Bridge WebSocket API — 多角色接入"

# Step 2: test-plan → .artifacts/test-plans/cs-plan-bridge.md
/dev-loop-skills:skill-2-test-plan-generator

# Step 3: test-code → tests/unit/test_bridge_api.py（在 submodule 内）
/dev-loop-skills:skill-3-test-code-writer

# Step 4: TDD 实现 → 注册 .artifacts/code-diffs/cs-diff-bridge.md
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-bridge

# Step 5: test-run → .artifacts/e2e-reports/cs-report-bridge.md
/dev-loop-skills:skill-4-test-runner

# Step 6: 链条验证
/dev-loop-skills:skill-6-artifact-registry
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-bridge.md` 存在，0 FAIL 0 SKIP。

---

## 文件清单

| 源文件 | 测试文件 | 行数 | 内容 |
|--------|---------|------|------|
| `bridge_api/__init__.py` | — | 2 | 包声明 |
| `bridge_api/ws_server.py` | `tests/unit/test_bridge_api.py` | ~150 | WebSocket server + 消息路由 |

---

## Task 3.1: ws_server.py

**Spec 参考:** `02-channel-server.md` §5 全部消息格式

- [ ] **写测试** `tests/unit/test_bridge_api.py`

```python
import pytest
from unittest.mock import MagicMock
from bridge_api.ws_server import BridgeAPIServer, BridgeConnection
from protocol.commands import parse_command

@pytest.fixture
def server():
    return BridgeAPIServer(conversation_manager=MagicMock(), port=0)

def test_parse_register(server):
    msg = {"type": "register", "bridge_type": "feishu",
           "instance_id": "fb-1", "capabilities": ["customer", "operator", "admin"]}
    conn = server._parse_register(msg)
    assert conn.bridge_type == "feishu"
    assert set(conn.capabilities) == {"customer", "operator", "admin"}

def test_customer_connect(server):
    msg = {"type": "customer_connect", "conversation_id": "feishu_oc_abc",
           "customer": {"id": "david", "name": "David"}}
    server._handle_customer_connect(msg)
    server._conversation_manager.create.assert_called_once()

def test_operator_command_hijack(server):
    msg = {"type": "operator_command", "conversation_id": "c1",
           "operator_id": "xiaoli", "command": "/hijack"}
    cmd = server._parse_operator_command(msg)
    assert cmd.name == "hijack"

def test_admin_command_status(server):
    msg = {"type": "admin_command", "admin_id": "laochen", "command": "/status"}
    cmd = server._parse_admin_command(msg)
    assert cmd.name == "status"

def test_visibility_routing_public():
    assert BridgeAPIServer.compute_visibility_targets("public") == {"customer", "operator", "admin"}

def test_visibility_routing_side():
    assert BridgeAPIServer.compute_visibility_targets("side") == {"operator", "admin"}

def test_visibility_routing_system():
    assert BridgeAPIServer.compute_visibility_targets("system") == {"operator", "admin"}

def test_register_creates_connection(server):
    msg = {"type": "register", "bridge_type": "web",
           "instance_id": "wb-1", "capabilities": ["customer"]}
    conn = server._parse_register(msg)
    assert conn.instance_id == "wb-1"
    assert conn.capabilities == ["customer"]
```

- [ ] **运行失败** → **实现 bridge_api/ws_server.py** → **运行通过** → **Commit**

---

## Task 3.2: 完整性验证 + Merge

- [ ] **运行测试**

```bash
uv run pytest tests/unit/test_bridge_api.py -v
```

Expected: 8 tests PASS

- [ ] **skill-4 + skill-6**
开发完成后，由人类操作 push + 更新 submodule 指针（参考 README-operator-manual.md）

开发完成后，由人类操作 merge（参考 README-operator-manual.md）。
Agent 只需确保所有测试通过且 artifact 链条完整。

---

## 完成标准

- [ ] `bridge_api/ws_server.py` 实现完整
- [ ] 8 个测试 PASS
- [ ] 支持 customer/operator/admin 三种角色消息
- [ ] visibility 路由正确（public→全部，side→operator+admin）
- [ ] commit 完成（由人类操作 merge）
