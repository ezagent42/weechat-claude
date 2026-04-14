# Channel-Server v1.0 — 操作手册

> 你（Allen）需要做的事：启动 session → 给 prompt → verify → commit/push
> Agent 自动做的事：读 plan、执行 dev-loop、写代码、跑测试

---

## 工作路径

```
所有操作:  ~/projects/zchat/                           ← feat/channel-server-v1 分支
代码开发:  ~/projects/zchat/zchat-channel-server/      ← submodule（自己的分支）
plan/spec: ~/projects/zchat/docs/discuss/plan/          ← 本目录
.artifacts: ~/projects/zchat/.artifacts/                ← cs- 前缀
命名约定:  docs/discuss/plan/ARTIFACT-CONVENTION.md
```

**不使用 worktree。** 一切在主仓库的 `feat/channel-server-v1` 分支。

## 分支策略

```
zchat 主仓库:
  dev (稳定)                  ← 不直接操作
  feat/channel-server-v1      ← 当前开发分支
                                docs、artifacts、submodule 指针、zchat CLI

channel-server submodule:
  main (稳定)
  phase0-infra                ← Phase 0 ✅
  feat/protocol               ← Phase 1
  feat/engine                 ← Phase 2
  feat/bridge-api             ← Phase 3
  feat/server-v1              ← Phase 4

完成后: submodule merge → main, zchat PR feat/channel-server-v1 → dev
```

---

## 启动方式

```bash
cd ~/projects/zchat
git checkout feat/channel-server-v1
source claude.local.env
claude
```

---

## Phase 1 + Phase 5 并行

### Session A: Phase 1 — Protocol

```bash
tmux new-session -s cs-phase1
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
```

**Prompt：**
```
读取 docs/discuss/plan/02-phase1-protocol.md。
代码在 zchat-channel-server/ submodule。cd 进去，基于 phase0-infra 创建 feat/protocol。
Artifact: cs- 前缀（见 ARTIFACT-CONVENTION.md）。
完成标准: .artifacts/e2e-reports/cs-report-protocol.md 存在，0 FAIL 0 SKIP。
```

### Session B: Phase 5 — zchat CLI

```bash
tmux new-session -s cs-phase5
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
```

**Prompt：**
```
读取 docs/discuss/plan/06-phase5-zchat-cli.md。
修改 zchat/cli/（不是 submodule）。Artifact: cs- 前缀。
完成标准: .artifacts/e2e-reports/cs-report-cli.md 存在，0 FAIL 0 SKIP。
```

### 完成后

```bash
# submodule push
cd ~/projects/zchat/zchat-channel-server && git push origin feat/protocol

# 主仓库 commit
cd ~/projects/zchat
git add zchat-channel-server .artifacts/ zchat/cli/
git commit -m "feat: Phase 1 protocol + Phase 5 CLI config"
```

---

## Phase 2 + Phase 3 并行

```bash
# Session C: Phase 2
tmux new-session -s cs-phase2
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
# Prompt: "读取 docs/discuss/plan/03-phase2-engine.md。cd zchat-channel-server，基于 feat/protocol 创建 feat/engine。cs- 前缀。"

# Session D: Phase 3
tmux new-session -s cs-phase3
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
# Prompt: "读取 docs/discuss/plan/04-phase3-bridge.md。cd zchat-channel-server，基于 feat/protocol 创建 feat/bridge-api。cs- 前缀。"
```

---

## Phase 4 — 集成

```bash
tmux new-session -s cs-phase4
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
# Prompt: "读取 docs/discuss/plan/05-phase4-integration.md。cd zchat-channel-server，创建 feat/server-v1。需要 E2E（ergo）。cs- 前缀。"
```

---

## Phase 4.5 — 飞书 Bridge（Phase 4 之后）

```bash
tmux new-session -s cs-feishu
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
```

**Prompt：**
```
读取 docs/discuss/plan/05b-phase4.5-feishu-bridge.md。
cd zchat-channel-server，基于 feat/server-v1 创建 feat/feishu-bridge。
参考 /tmp/cc-openclaw/feishu/message_parsers.py 的消息解析器模式。
Artifact: cs- 前缀。完成标准: .artifacts/e2e-reports/cs-report-feishu.md 0 FAIL 0 SKIP。
```

---

## Phase Final — 飞书全自动 E2E（Phase 4.5 之后）

**前提：3 个飞书测试群已创建，bot 已加入，feishu-e2e-config.yaml 已配置。**

```bash
tmux new-session -s cs-final
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
```

**Prompt：**
```
读取 docs/discuss/plan/07-phase-final-testing.md。
cd zchat-channel-server。所有 Phase 已完成（含飞书 Bridge）。
运行三层验收: unit 回归 + E2E Bridge API + 飞书全自动 E2E。
Artifact: cs- 前缀。完成标准: .artifacts/e2e-reports/cs-report-prerelease.md 0 FAIL 0 SKIP。
```

---

## 每个 Phase 完成后

```
□ .artifacts/ 有 cs-* 链条 (eval → plan → diff → report)
□ cd zchat-channel-server && uv run pytest tests/unit/ -v → 全 PASS
□ submodule push: cd zchat-channel-server && git push origin {branch}
□ 主仓库 commit: git add zchat-channel-server .artifacts/ && git commit
```

---

## 故障恢复

```bash
cd ~/projects/zchat && git checkout feat/channel-server-v1
source claude.local.env && claude
# "继续执行。检查 zchat-channel-server/ 内 git log 和测试状态，从断点继续。"
```
