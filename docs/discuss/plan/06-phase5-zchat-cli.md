# Phase 5: zchat CLI 配置扩展

> **工作位置:** ~/projects/zchat/ (feat/channel-server-v1 分支)
> **仓库:** zchat 主仓库
> **Spec 参考:** `spec/channel-server/02-channel-server.md` §8 配置 + `07-migration-plan.md` Phase 5
> **预估:** 1h
> **依赖:** Phase 0 完成即可开始
> **可并行:** 与 Phase 1 (protocol/) 并行

---

## 工作环境

**你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。**
这个 Phase 修改的是 **zchat 自身的代码**（不是 channel-server submodule）。
commit 到 feat/channel-server-v1 分支。

```bash
# 验证 zchat 项目
ls zchat/cli/project.py          # 要修改的文件
uv run pytest tests/unit/ -v     # 现有测试基线
```

修改范围: `zchat/cli/project.py` + `zchat/cli/templates/`。

---

## Dev-loop 闭环（6 步 → e2e-report 结束）

**Artifact 命名约定:** 见 `ARTIFACT-CONVENTION.md`，所有 ID 用 `cs-` 前缀。

```bash
# Step 1: eval-doc → .artifacts/eval-docs/cs-eval-cli.md
/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "zchat CLI 扩展 — channel-server v1.0 配置"

# Step 2: test-plan → .artifacts/test-plans/cs-plan-cli.md
/dev-loop-skills:skill-2-test-plan-generator

# Step 3: test-code → tests/unit/test_config_channel_server.py
/dev-loop-skills:skill-3-test-code-writer

# Step 4: TDD 实现 → 注册 .artifacts/code-diffs/cs-diff-cli.md
/dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-cli

# Step 5: test-run → .artifacts/e2e-reports/cs-report-cli.md
/dev-loop-skills:skill-4-test-runner

# Step 6: 链条验证
/dev-loop-skills:skill-6-artifact-registry
```

**闭环完成标志:** `.artifacts/e2e-reports/cs-report-cli.md` 存在，0 FAIL 0 SKIP。

---

## Task 5.1: config.toml 新增 [channel_server] 段

**Spec 参考:** `02-channel-server.md` §8 配置

- [ ] **写测试** `tests/unit/test_config_channel_server.py`

```python
import tomllib

def test_default_config_has_channel_server(tmp_path):
    from zchat.cli.project import generate_default_config
    text = generate_default_config("test-project", server="127.0.0.1", port=6667)
    config = tomllib.loads(text)
    assert "channel_server" in config
    assert config["channel_server"]["bridge_port"] == 9999
    assert config["channel_server"]["timers"]["takeover_wait"] == 180
    assert config["channel_server"]["participants"]["max_operator_concurrent"] == 5
```

- [ ] **修改 `zchat/cli/project.py`** — 在默认配置模板中添加:

```toml
[channel_server]
bridge_port = 9999
plugins_dir = "plugins"
db_path = "conversations.db"

[channel_server.timers]
takeover_wait = 180
idle_timeout = 300
close_timeout = 3600

[channel_server.participants]
operators = []
bridge_prefixes = ["feishu-bridge", "web-bridge"]
max_operator_concurrent = 5
```

- [ ] **测试通过** → **Commit**

---

## Task 5.2: Agent 模板

- [ ] **创建模板文件**

```
zchat/cli/templates/fast-response/
├── template.toml
└── soul.md

zchat/cli/templates/deep-thinking/
├── template.toml
└── soul.md
```

- [ ] **验证 template_loader 发现新模板**

```bash
uv run pytest tests/unit/test_template_loader.py -v
```

- [ ] **Commit**

---

## Task 5.3: submodule 更新 + Merge

```bash
cd ~/projects/zchat
git submodule update --remote zchat-channel-server
git add zchat-channel-server
git commit -m "chore: update channel-server to v1.0"
```

开发完成后，由人类在 wt 中 commit（参考 README-operator-manual.md）

---

## 完成标准

- [ ] `zchat project create` 生成的 config.toml 包含 `[channel_server]` 段
- [ ] 2 个 agent 模板可用
- [ ] channel-server submodule 指向 v1.0
