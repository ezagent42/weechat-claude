# Phase 0: 基础设施搭建

> **执行位置:** `~/projects/zchat/`（dev 分支），cd 进 `zchat-channel-server/` submodule（phase0-infra 分支）
> **仓库:** zchat-channel-server submodule（独立仓库）
> **Spec 参考:** `spec/channel-server/02-channel-server.md` §2 文件结构
> **预估:** 0.5h
> **依赖:** 无

---

## Agent 启动指令

```bash
# 1. 进入 submodule 并切到 phase0-infra 分支
cd zchat-channel-server
git checkout phase0-infra

# 2. 加载 skill（如果在 zchat 项目中有 dev-loop-skills）
# /dev-loop-skills:using-dev-loop
```

---

## Task 0.1: 测试目录重组

**目标:** 把现有的平铺测试文件拆成 unit/e2e/pre_release 三层。

**现有状态:** `tests/test_channel_server.py` 包含 12 个测试（message + sys_message + instructions）。

### 步骤

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p tests/unit tests/e2e tests/pre_release
mkdir -p plugins
touch tests/__init__.py tests/unit/__init__.py tests/e2e/__init__.py
echo "# Channel-server plugins directory\nApp plugins go here." > plugins/README.md
```

- [ ] **Step 2: 拆分现有测试**

将 `tests/test_channel_server.py` 拆为两个文件：

**tests/unit/test_message.py** — message.py 的测试（detect_mention, clean_mention, chunk_message）：
```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from message import detect_mention, clean_mention, chunk_message

def test_detect_mention():
    assert detect_mention("@alice-agent0 hello", "alice-agent0") is True
    assert detect_mention("hello @alice-agent0", "alice-agent0") is True
    assert detect_mention("hello everyone", "alice-agent0") is False

def test_clean_mention():
    assert clean_mention("@alice-agent0 hello", "alice-agent0") == "hello"

def test_chunk_message_short():
    assert chunk_message("short") == ["short"]

def test_chunk_message_long():
    text = "a" * 5000
    chunks = chunk_message(text, max_bytes=400)
    assert len(chunks) > 1
    assert all(len(c.encode("utf-8")) <= 400 for c in chunks)

def test_chunk_message_cjk():
    text = "你好" * 200
    chunks = chunk_message(text, max_bytes=390)
    assert len(chunks) > 1
    assert all(len(c.encode("utf-8")) <= 390 for c in chunks)

def test_chunk_message_strips_newlines():
    text = "line1\nline2\r\nline3"
    chunks = chunk_message(text)
    for chunk in chunks:
        assert "\n" not in chunk
        assert "\r" not in chunk

def test_detect_mention_with_dash_separator():
    assert detect_mention("@alice-helper hello", "alice-helper") is True
    assert detect_mention("@alice:helper hello", "alice-helper") is False
```

**tests/unit/test_legacy.py** — sys_message + instructions 测试：
```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from server import load_instructions
from zchat_protocol.sys_messages import encode_sys_for_irc, decode_sys_from_irc, make_sys_message

def test_sys_message_irc_roundtrip():
    msg = make_sys_message("alice-agent0", "sys.stop_request", {"reason": "test"})
    encoded = encode_sys_for_irc(msg)
    decoded = decode_sys_from_irc(encoded)
    assert decoded["type"] == "sys.stop_request"
    assert decoded["body"]["reason"] == "test"

def test_sys_message_not_user_text():
    assert decode_sys_from_irc("{this is just json-like text}") is None
    assert decode_sys_from_irc("hello world") is None

def test_load_instructions_interpolates_agent_name():
    result = load_instructions("alice-agent0")
    assert "alice-agent0" in result
    assert "$agent_name" not in result

def test_load_instructions_contains_routing_rules():
    result = load_instructions("test-agent")
    assert "/zchat:reply" in result

def test_load_instructions_contains_soul_pointer():
    result = load_instructions("test-agent")
    assert "soul.md" in result
```

- [ ] **Step 3: 删除旧文件**

```bash
rm tests/test_channel_server.py
```

- [ ] **Step 4: 创建 pytest.ini**

```ini
[pytest]
testpaths = tests
markers =
    e2e: end-to-end tests requiring ergo + channel-server
    prerelease: pre-release acceptance tests
asyncio_mode = auto
```

- [ ] **Step 5: 验证测试通过**

```bash
uv run pytest tests/unit/ -v
```

Expected: 12 tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/ pytest.ini
git rm tests/test_channel_server.py
git commit -m "chore: restructure tests into unit/e2e/pre_release layers"
```

---

## Task 0.2: 更新 pyproject.toml

- [ ] **Step 1: 添加新依赖 + 更新 build 配置**

```toml
[project]
name = "zchat-channel-server"
version = "1.0.0-dev"
dependencies = [
    "mcp[cli]>=1.2.0",
    "irc>=20.0",
    "zchat-protocol>=0.1.0",
    "websockets>=12.0",
]

[tool.hatch.build.targets.wheel]
packages = ["protocol", "engine", "transport", "bridge_api", "."]
only-include = [
    "server.py", "message.py", "instructions.md",
    "protocol/", "engine/", "transport/", "bridge_api/",
]
```

- [ ] **Step 2: uv sync 验证**

```bash
uv sync
uv run pytest tests/unit/ -v
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: update pyproject.toml for v1.0 module structure"
```

---

## Task 0.3: dev-loop-skills bootstrap

- [ ] **Step 1: 运行 skill-0**

```
/dev-loop-skills:skill-0-project-builder
```

这会生成 `.artifacts/` 目录和 skill-1 知识库。

- [ ] **Step 2: 验证 skill-1 可用**

```
/project-discussion-channel-server
问: "channel-server 当前有哪些 MCP tools?"
预期: 返回 reply + join_channel
```

- [ ] **Step 3: Commit**

```bash
git add .artifacts/ .claude/
git commit -m "chore: bootstrap dev-loop-skills"
```

---

## 完成标准

- [ ] `tests/unit/` 有 test_message.py + test_legacy.py，12 tests PASS
- [ ] `tests/e2e/` 和 `tests/pre_release/` 目录已创建
- [ ] `pyproject.toml` 更新，`uv sync` 成功
- [ ] dev-loop-skills bootstrap 完成，skill-1 可查询
- [ ] 所有改动已 commit 到 main
