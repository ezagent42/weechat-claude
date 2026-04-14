# Phase 1: Protocol 模块

> **Submodule 分支:** `feat/protocol`
> **仓库:** zchat-channel-server submodule
> **Spec 参考:** `spec/channel-server/01-protocol-primitives.md` (全部 10 个 section)
> **预估:** 2-3h
> **依赖:** Phase 0 完成
> **可并行:** 与 Phase 5 (zchat CLI) 并行

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
代码开发在 `zchat-channel-server/` submodule 内（独立 git 仓库）。

```bash
# 进入 submodule
cd zchat-channel-server

# 基于 phase0-infra 创建新分支
git checkout phase0-infra
git checkout -b feat/protocol

# 验证 Phase 0 已完成
uv run pytest tests/unit/ -v  # 应有 12 个 PASS

# 创建 protocol/ 目录
mkdir -p protocol
```

- 所有 `protocol/*.py` 和 `tests/unit/test_*.py` 在 submodule 内创建
- `.artifacts/` 在 zchat 根目录（`cd ..` 后可见）
- plan 文档在 `docs/discuss/plan/` 只读引用

---

## Dev-loop 闭环（6 步 → e2e-report 结束）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc → .artifacts/eval-docs/cs-eval-protocol.md
/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "通用对话协议原语层"

# Step 2: test-plan → .artifacts/test-plans/cs-plan-protocol.md
/dev-loop-skills:skill-2-test-plan-generator
# 输入: eval-doc + spec/01-protocol-primitives.md（在 ~/projects/zchat/ 只读引用）

# Step 3: test-code → tests/unit/test_*.py（在 submodule 内）
/dev-loop-skills:skill-3-test-code-writer

# Step 4: TDD 实现 → 注册 .artifacts/code-diffs/cs-diff-protocol.md
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-protocol

# Step 5: test-run → .artifacts/e2e-reports/cs-report-protocol.md
/dev-loop-skills:skill-4-test-runner
# 必须全部 PASS，无 skip

# Step 6: 链条验证
/dev-loop-skills:skill-6-artifact-registry
# registry.json 中 cs-eval-protocol → cs-plan-protocol → cs-diff-protocol → cs-report-protocol
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-protocol.md` 存在，0 FAIL 0 SKIP。

---

## 文件清单

| 源文件 | 测试文件 | 行数估算 | 内容 |
|--------|---------|---------|------|
| `protocol/__init__.py` | — | 2 | 包声明 |
| `protocol/conversation.py` | `tests/unit/test_conversation.py` | ~60 | Conversation + State + Resolution |
| `protocol/participant.py` | `tests/unit/test_participant.py` | ~30 | Participant + Role |
| `protocol/mode.py` | `tests/unit/test_mode.py` | ~50 | Mode + Transitions |
| `protocol/message_types.py` | — | ~40 | Message + Visibility |
| `protocol/gate.py` | `tests/unit/test_gate.py` | ~40 | gate_message() 纯函数 |
| `protocol/timer.py` | — | ~30 | Timer + TimerAction |
| `protocol/event.py` | `tests/unit/test_event.py` | ~40 | Event + EventType |
| `protocol/commands.py` | `tests/unit/test_commands.py` | ~60 | 命令解析 |

**总计:** ~350 行源码 + ~200 行测试

---

## Task 1.1: conversation.py

**Spec 参考:** `01-protocol-primitives.md §1`

- [ ] **写测试** `tests/unit/test_conversation.py`

```python
import pytest
from protocol.conversation import (
    Conversation, ConversationState, ConversationResolution,
    create_conversation, transition_state, VALID_STATE_TRANSITIONS,
)

def test_create_conversation():
    conv = create_conversation("feishu_oc_abc", metadata={"source": "feishu"})
    assert conv.id == "feishu_oc_abc"
    assert conv.state == ConversationState.CREATED
    assert conv.metadata["source"] == "feishu"

def test_activate():
    conv = create_conversation("test_1")
    transition_state(conv, ConversationState.ACTIVE)
    assert conv.state == ConversationState.ACTIVE

def test_idle_and_reactivate():
    conv = create_conversation("test_2")
    transition_state(conv, ConversationState.ACTIVE)
    transition_state(conv, ConversationState.IDLE)
    assert conv.state == ConversationState.IDLE
    transition_state(conv, ConversationState.ACTIVE)
    assert conv.state == ConversationState.ACTIVE

def test_resolve_directly_from_active():
    conv = create_conversation("test_3")
    transition_state(conv, ConversationState.ACTIVE)
    transition_state(conv, ConversationState.CLOSED)
    assert conv.state == ConversationState.CLOSED

def test_invalid_transition_raises():
    conv = create_conversation("test_4")
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_state(conv, ConversationState.IDLE)

def test_resolution():
    conv = create_conversation("test_5")
    conv.resolution = ConversationResolution(
        outcome="resolved", resolved_by="xiaoli", csat_score=5
    )
    assert conv.resolution.csat_score == 5
```

- [ ] **运行失败** → **实现** `protocol/conversation.py`（见 spec §1）→ **运行通过** → **Commit**

---

## Task 1.2: participant.py

**Spec 参考:** `01-protocol-primitives.md §2`

- [ ] **写测试** `tests/unit/test_participant.py`

```python
from protocol.participant import Participant, ParticipantRole

def test_create_customer():
    p = Participant(id="david", role=ParticipantRole.CUSTOMER)
    assert p.role == ParticipantRole.CUSTOMER

def test_create_agent():
    p = Participant(id="fast-agent", role=ParticipantRole.AGENT)
    assert p.role == ParticipantRole.AGENT

def test_roles_are_distinct():
    assert len(set(ParticipantRole)) == 4
```

- [ ] **运行失败** → **实现** → **运行通过** → **Commit**

---

## Task 1.3: mode.py

**Spec 参考:** `01-protocol-primitives.md §3`

- [ ] **写测试** `tests/unit/test_mode.py`

```python
import pytest
from protocol.mode import ConversationMode, validate_transition, VALID_MODE_TRANSITIONS

def test_auto_to_copilot():
    t = validate_transition(ConversationMode.AUTO, ConversationMode.COPILOT,
                           trigger="operator_joined", triggered_by="xiaoli")
    assert t.to_mode == ConversationMode.COPILOT

def test_copilot_to_takeover():
    t = validate_transition(ConversationMode.COPILOT, ConversationMode.TAKEOVER,
                           trigger="/hijack", triggered_by="xiaoli")
    assert t.trigger == "/hijack"

def test_takeover_to_auto():
    validate_transition(ConversationMode.TAKEOVER, ConversationMode.AUTO,
                       trigger="/release", triggered_by="xiaoli")

def test_auto_to_auto_invalid():
    with pytest.raises(ValueError):
        validate_transition(ConversationMode.AUTO, ConversationMode.AUTO,
                           trigger="noop", triggered_by="test")

def test_all_valid_transitions_count():
    assert len(VALID_MODE_TRANSITIONS) == 6
```

- [ ] **运行失败** → **实现** → **运行通过** → **Commit**

---

## Task 1.4: message_types.py + gate.py

**Spec 参考:** `01-protocol-primitives.md §4 §5`

- [ ] **写测试** `tests/unit/test_gate.py` — **这是协议最关键的测试**

```python
from protocol.message_types import MessageVisibility
from protocol.participant import Participant, ParticipantRole
from protocol.conversation import Conversation, ConversationState
from protocol.mode import ConversationMode
from protocol.gate import gate_message

def _conv(mode: ConversationMode) -> Conversation:
    c = Conversation(id="t", state=ConversationState.ACTIVE)
    c.mode = mode.value
    return c

# AUTO
def test_auto_agent_public():
    assert gate_message(_conv(ConversationMode.AUTO),
        Participant(id="a", role=ParticipantRole.AGENT),
        MessageVisibility.PUBLIC) == MessageVisibility.PUBLIC

# COPILOT — operator public 降级为 side
def test_copilot_operator_downgraded():
    assert gate_message(_conv(ConversationMode.COPILOT),
        Participant(id="op", role=ParticipantRole.OPERATOR),
        MessageVisibility.PUBLIC) == MessageVisibility.SIDE

def test_copilot_agent_passes():
    assert gate_message(_conv(ConversationMode.COPILOT),
        Participant(id="a", role=ParticipantRole.AGENT),
        MessageVisibility.PUBLIC) == MessageVisibility.PUBLIC

# TAKEOVER — agent public 降级为 side
def test_takeover_agent_downgraded():
    assert gate_message(_conv(ConversationMode.TAKEOVER),
        Participant(id="a", role=ParticipantRole.AGENT),
        MessageVisibility.PUBLIC) == MessageVisibility.SIDE

def test_takeover_operator_passes():
    assert gate_message(_conv(ConversationMode.TAKEOVER),
        Participant(id="op", role=ParticipantRole.OPERATOR),
        MessageVisibility.PUBLIC) == MessageVisibility.PUBLIC

# Side/System 不受影响
def test_side_stays_side():
    assert gate_message(_conv(ConversationMode.AUTO),
        Participant(id="a", role=ParticipantRole.AGENT),
        MessageVisibility.SIDE) == MessageVisibility.SIDE

def test_system_stays_system():
    assert gate_message(_conv(ConversationMode.TAKEOVER),
        Participant(id="a", role=ParticipantRole.AGENT),
        MessageVisibility.SYSTEM) == MessageVisibility.SYSTEM
```

- [ ] **运行失败** → **实现 message_types.py + gate.py** → **运行通过** → **Commit**

---

## Task 1.5: event.py + timer.py + commands.py

**Spec 参考:** `01-protocol-primitives.md §6 §7 §8`

- [ ] **写测试** `tests/unit/test_event.py` + `tests/unit/test_commands.py`

```python
# tests/unit/test_event.py
from protocol.event import Event, EventType

def test_event_creation():
    e = Event(type=EventType.CONVERSATION_CREATED, conversation_id="t1", data={})
    assert e.id  # auto UUID

def test_event_types_complete():
    for name in ["CONVERSATION_CREATED", "MODE_CHANGED", "MESSAGE_SENT",
                 "MESSAGE_GATED", "TIMER_EXPIRED", "SLA_BREACH",
                 "SQUAD_ASSIGNED", "CONVERSATION_RESOLVED"]:
        assert hasattr(EventType, name)
```

```python
# tests/unit/test_commands.py
from protocol.commands import parse_command

def test_parse_hijack():
    cmd = parse_command("/hijack")
    assert cmd.name == "hijack"

def test_parse_dispatch():
    cmd = parse_command("/dispatch feishu_oc_abc deep-agent")
    assert cmd.args["conversation_id"] == "feishu_oc_abc"
    assert cmd.args["agent_nick"] == "deep-agent"

def test_parse_assign():
    cmd = parse_command("/assign fast-agent xiaoli")
    assert cmd.args["agent_nick"] == "fast-agent"

def test_non_command():
    assert parse_command("hello") is None

def test_unknown_command():
    cmd = parse_command("/foobar")
    assert cmd.name == "unknown"
```

- [ ] **运行失败** → **实现 event.py + timer.py + commands.py** → **运行通过** → **Commit**

---

## Task 1.6: 完整性验证 + Merge

- [ ] **运行 protocol/ 全部测试**

```bash
uv run pytest tests/unit/test_conversation.py tests/unit/test_participant.py \
  tests/unit/test_mode.py tests/unit/test_gate.py tests/unit/test_event.py \
  tests/unit/test_commands.py -v
```

Expected: ~25 tests PASS

- [ ] **运行 dev-loop skill-4 生成报告**

```
/dev-loop-skills:skill-4-test-runner
```

- [ ] **注册 artifact**

```
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-protocol
```

开发完成后，由人类操作 push + 更新 submodule 指针（参考 README-operator-manual.md）

开发完成后，由人类操作 merge（参考 README-operator-manual.md 的 merge 流程）。
Agent 只需确保所有测试通过且 artifact 链条完整。

---

## 完成标准

- [ ] `protocol/` 下 8 个 .py 文件全部存在
- [ ] 6 个测试文件共 ~25 个测试全部 PASS
- [ ] 无外部依赖（纯 Python stdlib）
- [ ] artifact 已注册
- [ ] commit 完成（由人类操作 merge）
