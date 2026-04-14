# Channel-Server v1.0 — 开发计划索引

> 每个文档独立可执行，agent 只需读取对应文档即可开始工作。
> Spec 源: `docs/discuss/spec/channel-server/`
> PRD 源: `docs/discuss/prd/`

---

## 执行顺序与依赖

```
Phase 0 (phase0-infra) ── 必须先完成
    │
    ├── Phase 1 (feat/protocol) ──┐
    │                              ├── 可并行
    └── Phase 5 (zchat CLI)  ─────┘
            │
            │ Phase 1 push 后
            ├── Phase 2 (feat/engine) ────┐
            │                              ├── 可并行
            └── Phase 3 (feat/bridge-api) ┘
                        │
                        │ Phase 2+3 merge 后
                        └── Phase 4 (feat/server-v1)
                                │
                                └── Phase 4.5 (feat/feishu-bridge)
                                        │
                                        └── Phase Final (飞书全自动 E2E)
```

## 操作手册

**[README-operator-manual.md](README-operator-manual.md)** — 如何用多个 tmux session 跑 Claude Code 自动开发。包含每个 Phase 的完整 prompt、merge 流程、故障恢复。

---

## 文档清单

| 文档 | 用途 | submodule 分支 | 依赖 | 预估 |
|------|------|---------------|------|------|
| `01-phase0-infra.md` | 基础设施搭建 + dev-loop 初始化 | `phase0-infra` | 无 | 0.5h |
| `02-phase1-protocol.md` | protocol/ 目录：8 个协议原语模块 | `feat/protocol` | Phase 0 | 2-3h |
| `03-phase2-engine.md` | engine/ 目录：8 个运行时模块 | `feat/engine` | Phase 1 | 3-4h |
| `04-phase3-bridge.md` | bridge_api/ 目录：WebSocket server | `feat/bridge-api` | Phase 1 | 1-2h |
| `05-phase4-integration.md` | transport/ + server.py 重构 + E2E | `feat/server-v1` | Phase 2+3 | 3-4h |
| `05b-phase4.5-feishu-bridge.md` | 飞书 Bridge：消息解析+群映射+visibility 路由 | `feat/feishu-bridge` | Phase 4 | 3-4h |
| `06-phase5-zchat-cli.md` | zchat CLI 配置扩展 + 模板 | (feat/channel-server-v1) | Phase 0 | 1h |
| `07-phase-final-testing.md` | Pre-release 验收（含飞书全自动 E2E） | — | Phase 4.5 | 3-4h |

## 每个 agent 的启动指令

每个文档开头都包含以下信息，agent 可以直接执行：

1. **Worktree 创建命令** — `git worktree add ...`
2. **需要加载的 skill** — dev-loop-skills + project-discussion
3. **Spec 参考文档** — 哪个 spec 文件的哪个 section
4. **Dev-loop 闭环步骤** — eval-doc → test-plan → test-code → implement → test-run
5. **验收标准** — 全部测试通过 + artifact 注册

## 测试架构

```
channel-server 测试:
  Unit:        uv run pytest tests/unit/ -v              (每个 Phase 都有)
  E2E:         uv run pytest tests/e2e/ -v -m e2e        (Phase 4)
  Pre-release: uv run pytest tests/pre_release/ -v -m prerelease  (Phase Final)

zchat 测试:
  Unit:        uv run pytest tests/unit/ -v              (Phase 5)
```

---

*索引创建于 2026-04-14 · 基于 08-implementation-plan.md 拆分*
