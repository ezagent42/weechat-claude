# Phase Final: Pre-release 验收测试

> **执行位置:** `~/projects/zchat/`（feat/channel-server-v1 分支）
> **仓库:** zchat-channel-server submodule
> **Spec 参考:** `spec/channel-server/05-user-journeys.md` + `09-feishu-bridge.md §7`
> **预估:** 3-4h
> **依赖:** Phase 4.5 (飞书 Bridge) 完成

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
所有 Phase 1-4.5 在 submodule 内已完成。

```bash
cd zchat-channel-server

# 确认所有模块可用
uv run python -c "
from protocol.gate import gate_message
from engine.conversation_manager import ConversationManager
from bridge_api.ws_server import BridgeAPIServer
from transport.irc_transport import IRCTransport
from feishu_bridge.message_parsers import parse_message
from feishu_bridge.test_client import FeishuTestClient
print('All v1.0 modules + feishu_bridge OK')
"

# 确认 unit + E2E 基线全部通过
uv run pytest tests/unit/ tests/e2e/ feishu_bridge/tests/ -v
```

**依赖:** Phase 4.5 (飞书 Bridge) 必须已完成。

---

## Dev-loop 闭环（6 步 — verify 模式）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc (verify 模式)
/dev-loop-skills:skill-5-feature-eval verify
# 主题: "channel-server v1.0 端到端验收（含飞书真实环境）"

# Step 2: test-plan → .artifacts/test-plans/cs-plan-prerelease.md
/dev-loop-skills:skill-2-test-plan-generator

# Step 3: test-code → tests/pre_release/*.py
/dev-loop-skills:skill-3-test-code-writer

# Step 4: 执行验收测试

# Step 5: test-run → .artifacts/e2e-reports/cs-report-prerelease.md
/dev-loop-skills:skill-4-test-runner

# Step 6: artifact 注册
/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-prerelease
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-prerelease.md` 存在，0 FAIL 0 SKIP。

---

## 三层验收

### Layer 1: Unit 回归（所有 Phase 测试）

```bash
uv run pytest tests/unit/ feishu_bridge/tests/ -v
```

Expected: ~70+ tests PASS

### Layer 2: E2E — Bridge API（无需飞书凭证）

```bash
uv run pytest tests/e2e/ -v -m e2e --timeout=30
```

通过 WebSocket 模拟 Bridge，验证协议行为（conversation lifecycle, mode switching, gate enforcement）。

### Layer 3: Pre-release — 飞书真实环境（需要飞书凭证）

**前提：**
- `.feishu-credentials.json` 存在（app_id + app_secret）
- 3 个飞书测试群已创建，bot 已加入
- `feishu-e2e-config.yaml` 配置正确

---

## 飞书 E2E 测试群配置

### 需要的飞书群

| 群名 | chat_id 配置项 | 用途 | 成员 |
|------|--------------|------|------|
| `[测试]客户对话` | `customer_chat` | 模拟客户聊天 | bot |
| `[测试]小李分队` | `squad_chat` | 模拟人工客服工作区 | bot |
| `[测试]管理群` | `admin_chat` | 模拟管理员操作 | bot |

### 配置文件

```yaml
# tests/pre_release/feishu-e2e-config.yaml
feishu:
  app_id: ${FEISHU_APP_ID}
  app_secret: ${FEISHU_APP_SECRET}

groups:
  customer_chat: "oc_customer_test_xxx"
  squad_chat: "oc_squad_test_xxx"
  admin_chat: "oc_admin_test_xxx"

channel_server:
  bridge_port: 9999
  irc_port: 6667
```

---

## 飞书 E2E 测试代码

```python
# tests/pre_release/test_feishu_e2e.py
"""全自动飞书 E2E 测试 — 6 步状态机完整走通"""

import time
import pytest
import yaml
from feishu_bridge.test_client import FeishuTestClient

@pytest.fixture(scope="module")
def feishu_config():
    with open("tests/pre_release/feishu-e2e-config.yaml") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="module")
def feishu(feishu_config):
    cfg = feishu_config["feishu"]
    return FeishuTestClient(cfg["app_id"], cfg["app_secret"])

@pytest.fixture(scope="module")
def groups(feishu_config):
    return feishu_config["groups"]

@pytest.fixture(scope="module")
def full_stack():
    """启动 ergo + channel-server + feishu_bridge"""
    # ... 启动进程 ...
    yield
    # ... 清理 ...


@pytest.mark.prerelease
class TestFeishuFullJourney:
    """PRD 6 步状态机端到端验证"""

    def test_step1_customer_onboard(self, feishu, groups, full_stack):
        """US-2.1: 客户接入 → agent 回复"""
        feishu.send_message(groups["customer_chat"], "B 套餐多少钱")
        msg = feishu.assert_message_appears(
            groups["customer_chat"],
            contains="套餐",
            timeout=15
        )
        assert msg is not None

    def test_step2_squad_notification(self, feishu, groups, full_stack):
        """US-2.3: 分队群收到对话通知"""
        feishu.assert_message_appears(
            groups["squad_chat"],
            contains="进行中",
            timeout=10
        )

    def test_step3_copilot_gate(self, feishu, groups, full_stack):
        """US-2.4: copilot 模式 — operator 消息不到客户群"""
        # operator 加入
        feishu.send_message(groups["squad_chat"], "进入对话")
        time.sleep(3)

        # operator 发建议
        test_text = f"建议强调优惠_{int(time.time())}"  # 唯一标识
        feishu.send_message(groups["squad_chat"], test_text)
        time.sleep(5)

        # 验证: 客户群没有这条消息
        feishu.assert_message_absent(
            groups["customer_chat"],
            contains=test_text,
            wait=8
        )

        # 验证: 分队群有这条消息
        feishu.assert_message_appears(
            groups["squad_chat"],
            contains=test_text,
            timeout=3
        )

    def test_step4_hijack(self, feishu, groups, full_stack):
        """US-2.5: /hijack → takeover"""
        feishu.send_message(groups["squad_chat"], "/hijack")
        feishu.assert_message_appears(
            groups["squad_chat"],
            contains="takeover",
            timeout=10
        )

    def test_step5_operator_message_reaches_customer(self, feishu, groups, full_stack):
        """US-2.6: takeover 下人工消息到客户"""
        operator_text = f"您好我是客服小李_{int(time.time())}"
        feishu.send_message(groups["squad_chat"], operator_text)

        # 验证: 客户群收到
        feishu.assert_message_appears(
            groups["customer_chat"],
            contains="客服小李",
            timeout=10
        )

    def test_step6_resolve_and_csat(self, feishu, groups, full_stack):
        """US-2.6: /resolve → CSAT"""
        feishu.send_message(groups["squad_chat"], "/resolve")

        # 验证: 客户群收到 CSAT 卡片
        feishu.assert_message_appears(
            groups["customer_chat"],
            contains="评分",
            timeout=10
        )


@pytest.mark.prerelease
class TestFeishuGateIsolation:
    """Gate 强制执行验证 — 最关键的安全测试"""

    def test_takeover_agent_side_not_in_customer(self, feishu, groups, full_stack):
        """takeover 下 agent 消息降为 side，客户看不到"""
        # 需要先建立 takeover 状态
        # ...
        
        # agent 发消息（会被 gate 降为 side）
        # 验证: 分队群看到 [侧栏] 标签
        # 验证: 客户群看不到
        pass

    def test_copilot_operator_not_in_customer(self, feishu, groups, full_stack):
        """copilot 下 operator 消息降为 side，客户看不到"""
        pass


@pytest.mark.prerelease
class TestFeishuAdminCommands:
    """管理群命令测试"""

    def test_status_command(self, feishu, groups, full_stack):
        feishu.send_message(groups["admin_chat"], "/status")
        feishu.assert_message_appears(
            groups["admin_chat"],
            contains="active",
            timeout=10
        )
```

### 运行命令

```bash
# 需要飞书凭证
FEISHU_APP_ID=xxx FEISHU_APP_SECRET=xxx \
  uv run pytest tests/pre_release/test_feishu_e2e.py -v -m prerelease --timeout=120
```

---

## Walkthrough 录制

```bash
# asciinema 录制完整流程
asciinema rec tests/pre_release/evidence/feishu-e2e.cast -c \
  "uv run pytest tests/pre_release/ -v -m prerelease --timeout=120"
```

---

## 证据保存

```
tests/pre_release/evidence/
├── feishu-e2e.cast              # asciinema 录制
├── unit-regression.log          # unit 测试输出
├── e2e-bridge-api.log           # Bridge API E2E 输出
├── feishu-e2e.log               # 飞书 E2E 输出
└── gate-isolation.log           # Gate 隔离验证输出
```

---

## 完成标准

- [ ] Unit 回归: 全部 PASS (~70+ tests)
- [ ] E2E Bridge API: 全部 PASS (4 scenarios)
- [ ] 飞书 E2E 6 步状态机: 全部 PASS
- [ ] 飞书 Gate 隔离验证: 全部 PASS
- [ ] 飞书管理命令验证: 全部 PASS
- [ ] `.artifacts/e2e-reports/cs-report-prerelease.md` 存在，0 FAIL 0 SKIP
- [ ] evidence/ 目录有完整录制
