# Phase 2: Engine 模块

> **Submodule 分支:** `feat/engine`
> **仓库:** zchat-channel-server submodule
> **Spec 参考:** `spec/channel-server/02-channel-server.md` §3 核心模块设计
> **预估:** 3-4h
> **依赖:** Phase 1 (protocol/) commit 完成（由人类操作 merge）
> **可并行:** 与 Phase 3 (bridge_api/) 并行

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
代码开发在 `zchat-channel-server/` submodule 内。

```bash
cd zchat-channel-server

# 基于 Phase 1 完成的分支创建新分支
git checkout feat/protocol   # 或 Phase 1 merge 后的目标分支
git checkout -b feat/engine

# 验证 Phase 1 (protocol/) 已完成
uv run python -c "from protocol.conversation import Conversation; print('OK')"

mkdir -p engine
```

**依赖:** Phase 1 (protocol/) 的代码必须已存在于 submodule 的 `protocol/` 目录。

---

## Dev-loop 闭环（6 步 → e2e-report 结束）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc → .artifacts/eval-docs/cs-eval-engine.md
/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "对话引擎运行时"

# Step 2: test-plan → .artifacts/test-plans/cs-plan-engine.md
/dev-loop-skills:skill-2-test-plan-generator

# Step 3: test-code → tests/unit/test_*.py（在 submodule 内）
/dev-loop-skills:skill-3-test-code-writer

# Step 4: TDD 实现 → 注册 .artifacts/code-diffs/cs-diff-engine.md
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-engine

# Step 5: test-run → .artifacts/e2e-reports/cs-report-engine.md
/dev-loop-skills:skill-4-test-runner

# Step 6: 链条验证
/dev-loop-skills:skill-6-artifact-registry
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-engine.md` 存在，0 FAIL 0 SKIP。

---

## 文件清单

| 源文件 | 测试文件 | 行数 | 内容 |
|--------|---------|------|------|
| `engine/__init__.py` | — | 2 | 包声明 |
| `engine/event_bus.py` | `tests/unit/test_event_bus.py` | ~100 | 事件发布/订阅 + SQLite |
| `engine/conversation_manager.py` | `tests/unit/test_conversation_manager.py` | ~150 | CRUD + 状态机 + 并发上限 |
| `engine/mode_manager.py` | `tests/unit/test_mode_manager.py` | ~60 | 模式切换 + 事件发出 |
| `engine/timer_manager.py` | `tests/unit/test_timer_manager.py` | ~80 | asyncio 计时器 |
| `engine/message_store.py` | `tests/unit/test_message_store.py` | ~80 | 消息存储 + edit |
| `engine/plugin_manager.py` | `tests/unit/test_plugin_manager.py` | ~60 | 钩子加载 + 调用 |
| `engine/participant_registry.py` | `tests/unit/test_participant_registry.py` | ~50 | nick → role 映射 |
| `engine/squad_registry.py` | `tests/unit/test_squad_registry.py` | ~60 | 分队管理 |

**总计:** ~640 行源码 + ~300 行测试

---

## Task 2.1: event_bus.py (先实现，其他模块依赖它)

**Spec 参考:** `02-channel-server.md` §3.5 EventBus

- [ ] **写测试** `tests/unit/test_event_bus.py`

```python
import pytest
from protocol.event import Event, EventType
from engine.event_bus import EventBus

@pytest.fixture
def bus(tmp_path):
    return EventBus(str(tmp_path / "events.db"))

@pytest.mark.asyncio
async def test_publish_and_subscribe(bus):
    received = []
    bus.subscribe(EventType.CONVERSATION_CREATED, lambda e: received.append(e))
    await bus.publish(Event(type=EventType.CONVERSATION_CREATED, conversation_id="c1"))
    assert len(received) == 1

@pytest.mark.asyncio
async def test_persisted_to_sqlite(bus):
    await bus.publish(Event(type=EventType.MODE_CHANGED, conversation_id="c1",
                           data={"from": "auto", "to": "copilot"}))
    results = bus.query(conversation_id="c1")
    assert len(results) == 1
    assert results[0].type == EventType.MODE_CHANGED

@pytest.mark.asyncio
async def test_query_by_type(bus):
    await bus.publish(Event(type=EventType.MODE_CHANGED, conversation_id="c1"))
    await bus.publish(Event(type=EventType.MESSAGE_SENT, conversation_id="c1"))
    results = bus.query(event_type=EventType.MODE_CHANGED)
    assert len(results) == 1
```

- [ ] **运行失败** → **实现 engine/event_bus.py** → **运行通过** → **Commit**

---

## Task 2.2: conversation_manager.py

**Spec 参考:** `02-channel-server.md` §3.1 ConversationManager

- [ ] **写测试** `tests/unit/test_conversation_manager.py`

```python
import pytest
from engine.conversation_manager import ConversationManager, ConcurrencyLimitExceeded
from protocol.conversation import ConversationState
from protocol.participant import Participant, ParticipantRole

@pytest.fixture
def mgr(tmp_path):
    return ConversationManager(str(tmp_path / "conv.db"), max_operator_concurrent=2)

def test_create_and_get(mgr):
    conv = mgr.create("c1")
    assert mgr.get("c1").id == "c1"

def test_create_idempotent(mgr):
    mgr.create("c1")
    mgr.create("c1")  # 不报错，返回同一个
    assert mgr.get("c1") is not None

def test_lifecycle(mgr):
    mgr.create("c1")
    mgr.activate("c1")
    assert mgr.get("c1").state == ConversationState.ACTIVE
    mgr.idle("c1")
    assert mgr.get("c1").state == ConversationState.IDLE
    mgr.reactivate("c1")
    assert mgr.get("c1").state == ConversationState.ACTIVE

def test_operator_concurrency_limit(mgr):
    for i in range(3):
        mgr.create(f"c{i}")
        mgr.activate(f"c{i}")
    op = Participant(id="xiaoli", role=ParticipantRole.OPERATOR)
    mgr.add_participant("c0", op)
    mgr.add_participant("c1", op)
    with pytest.raises(ConcurrencyLimitExceeded):
        mgr.add_participant("c2", op)

def test_resolve(mgr):
    mgr.create("c1")
    mgr.activate("c1")
    mgr.resolve("c1", "resolved", "xiaoli")
    assert mgr.get("c1").state == ConversationState.CLOSED
    assert mgr.get("c1").resolution.outcome == "resolved"

def test_list_active(mgr):
    mgr.create("c1"); mgr.activate("c1")
    mgr.create("c2"); mgr.activate("c2")
    mgr.create("c3")  # CREATED, not active
    assert len(mgr.list_active()) == 2

def test_persistence_survives_restart(tmp_path):
    db = str(tmp_path / "conv.db")
    m1 = ConversationManager(db)
    m1.create("c1"); m1.activate("c1")
    del m1
    m2 = ConversationManager(db)
    assert m2.get("c1").state == ConversationState.ACTIVE
```

- [ ] **运行失败** → **实现** → **运行通过** → **Commit**

---

## Task 2.3: mode_manager.py + timer_manager.py

**Spec 参考:** `02-channel-server.md` §3.2 §3.4

- [ ] **写测试** `tests/unit/test_mode_manager.py` + `tests/unit/test_timer_manager.py`

```python
# tests/unit/test_mode_manager.py
import pytest
from engine.mode_manager import ModeManager
from engine.event_bus import EventBus
from protocol.conversation import Conversation, ConversationState
from protocol.mode import ConversationMode

@pytest.fixture
def mm(tmp_path):
    return ModeManager(EventBus(str(tmp_path / "e.db")))

def test_transition(mm):
    conv = Conversation(id="c1", state=ConversationState.ACTIVE)
    mm.transition(conv, ConversationMode.COPILOT, "operator_joined", "xiaoli")
    assert conv.mode == "copilot"

def test_invalid_raises(mm):
    conv = Conversation(id="c1", state=ConversationState.ACTIVE)
    with pytest.raises(ValueError):
        mm.transition(conv, ConversationMode.AUTO, "noop", "test")
```

```python
# tests/unit/test_timer_manager.py
import asyncio, pytest
from datetime import timedelta
from engine.timer_manager import TimerManager
from engine.event_bus import EventBus
from protocol.timer import TimerAction
from protocol.event import EventType

@pytest.fixture
def setup(tmp_path):
    bus = EventBus(str(tmp_path / "e.db"))
    return TimerManager(bus), bus

@pytest.mark.asyncio
async def test_timer_fires(setup):
    tm, bus = setup
    fired = []
    bus.subscribe(EventType.TIMER_EXPIRED, lambda e: fired.append(e))
    tm.set_timer("c1", "test", timedelta(seconds=0.1), TimerAction(type="event"))
    await asyncio.sleep(0.3)
    assert len(fired) == 1

@pytest.mark.asyncio
async def test_timer_cancel(setup):
    tm, bus = setup
    fired = []
    bus.subscribe(EventType.TIMER_EXPIRED, lambda e: fired.append(e))
    tm.set_timer("c1", "test", timedelta(seconds=0.5), TimerAction(type="event"))
    tm.cancel_timer("c1", "test")
    await asyncio.sleep(0.7)
    assert len(fired) == 0
```

- [ ] **运行失败** → **实现** → **运行通过** → **Commit**

---

## Task 2.4: message_store + plugin_manager + participant_registry + squad_registry

每个模块遵循相同 TDD 循环。关键测试点：

| 模块 | 关键测试 |
|------|---------|
| message_store | save → get → edit → query_by_conversation |
| plugin_manager | load_hooks_from_dir → call on_message → call on_mode_changed |
| participant_registry | register_agent → register_operator → identify(nick) |
| squad_registry | assign → get_squad → reassign → get_operator |

- [ ] 每个模块: **写测试** → **实现** → **通过** → **Commit**

---

## Task 2.5: 完整性验证 + Merge

- [ ] **运行 engine/ 全部测试**

```bash
uv run pytest tests/unit/ -v  # 包含 protocol + engine 的全部测试
```

Expected: ~50+ tests PASS

- [ ] **skill-4 生成报告 + skill-6 注册 artifact**
开发完成后，由人类操作 push + 更新 submodule 指针（参考 README-operator-manual.md）

开发完成后，由人类操作 merge（参考 README-operator-manual.md）。
Agent 只需确保所有测试通过且 artifact 链条完整。

---

## 完成标准

- [ ] `engine/` 下 8 个 .py 文件
- [ ] 8 个测试文件 ~30 个测试全部 PASS
- [ ] SQLite 持久化验证（重启后数据恢复）
- [ ] asyncio Timer 验证（设置/取消/超时）
- [ ] 并发上限验证（超限抛异常）
