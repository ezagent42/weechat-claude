# Channel-Server v1.0 — Artifact 命名约定

> 所有 dev-loop skill 产出的中间文件遵循此约定
> 目的：和 zchat 主库的 artifacts 共存于同一个 `.artifacts/` 目录不冲突

---

## 根目录

```
~/projects/zchat/.artifacts/      ← 所有 artifacts 统一存放
```

## ID 前缀

**channel-server 的所有 artifact ID 以 `cs-` 开头。**

| Phase | eval-doc ID | test-plan ID | code-diff ID | e2e-report ID |
|-------|------------|-------------|-------------|---------------|
| Phase 0 | — | — | — | — |
| Phase 1 | `cs-eval-protocol` | `cs-plan-protocol` | `cs-diff-protocol` | `cs-report-protocol` |
| Phase 2 | `cs-eval-engine` | `cs-plan-engine` | `cs-diff-engine` | `cs-report-engine` |
| Phase 3 | `cs-eval-bridge` | `cs-plan-bridge` | `cs-diff-bridge` | `cs-report-bridge` |
| Phase 4 | `cs-eval-server` | `cs-plan-server` | `cs-diff-server` | `cs-report-server` |
| Phase 5 | `cs-eval-cli` | `cs-plan-cli` | `cs-diff-cli` | `cs-report-cli` |
| Final | `cs-eval-prerelease` | `cs-plan-prerelease` | — | `cs-report-prerelease` |

## 文件路径

放在现有的类型子目录中，文件名对应 ID：

```
.artifacts/
├── eval-docs/
│   ├── eval-ctrl-c-orphan-007.md      ← 主库的
│   ├── cs-eval-protocol.md            ← channel-server Phase 1
│   ├── cs-eval-engine.md              ← channel-server Phase 2
│   └── ...
├── test-plans/
│   ├── plan-ctrl-c-cleanup-008.md     ← 主库的
│   ├── cs-plan-protocol.md            ← channel-server Phase 1
│   └── ...
├── code-diffs/
│   ├── diff-ctrl-c-cleanup-fix.md     ← 主库的
│   ├── cs-diff-protocol.md            ← channel-server Phase 1
│   └── ...
├── e2e-reports/
│   ├── report-ctrl-c-cleanup-001/     ← 主库的
│   ├── cs-report-protocol.md          ← channel-server Phase 1
│   └── ...
├── bootstrap/
│   ├── manifest.json                  ← 主库的 (zchat 整体)
│   ├── test-baseline.json             ← 主库的
│   ├── test-baseline-channel-server.json  ← channel-server 的
│   ├── module-reports/
│   │   ├── agent_manager.json         ← 主库的
│   │   ├── cs_server.json             ← channel-server 的
│   │   ├── cs_message.json            ← channel-server 的
│   │   └── ...
│   └── bootstrap-report.md            ← 主库的
└── registry.json                      ← 统一索引
```

## 在 Prompt 中的引用

每个 Phase 的 prompt 应该包含：

```
Artifact 命名约定（必须遵守）：
- 所有 artifact ID 以 cs- 开头
- eval-doc:   .artifacts/eval-docs/cs-eval-{phase}.md
- test-plan:  .artifacts/test-plans/cs-plan-{phase}.md  
- code-diff:  .artifacts/code-diffs/cs-diff-{phase}.md
- e2e-report: .artifacts/e2e-reports/cs-report-{phase}.md
- 注册到 .artifacts/registry.json
```

## 闭环完成标志

每个 Phase 完成时，`.artifacts/registry.json` 中应该有 4 条 `cs-*` 记录，链条完整：

```
cs-eval-{phase}   → status: confirmed
cs-plan-{phase}   → related_ids: [cs-eval-{phase}]
cs-diff-{phase}   → related_ids: [cs-plan-{phase}]
cs-report-{phase} → related_ids: [cs-diff-{phase}], status: pass (0 FAIL 0 SKIP)

链条: eval-doc → test-plan → code-diff → e2e-report (4 条全部存在)
```
