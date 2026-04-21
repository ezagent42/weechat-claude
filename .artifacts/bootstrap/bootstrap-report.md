# Bootstrap Report · zchat (main)

> Skill 0 · project-builder · 2026-04-21 V6 finalize 后重跑

## 环境

- Python 3.13.5, uv 已 ready
- ergo, zellij, jq 三件套已 ready
- 测试基线: 325 unit passed / 0 failed

## 项目

- 源文件 389 个，Python 118 个覆盖 117（99.2%）
- 仅 `.gitkeep` 占位文件未分析

## 11 模块

1. **app** — Typer CLI 根 + 所有子命令
2. **agent_manager** — Agent lifecycle（create/stop/restart/send）+ ready marker + auto-confirm watcher（phase 7 加新 Claude Code prompt 模式）
3. **irc_manager** — ergo daemon + WeeChat zellij tab + SASL auth injection
4. **project** — project CRUD + paths + defaults + global config
5. **routing** — routing.toml V6 schema read/write（bot + channel + entry_agent；agents 字段已删）
6. **zellij** — zellij subprocess 封装 + KDL layout
7. **auth** — OIDC device-code + ergo_auth_script
8. **runner** — template resolution + env 渲染
9. **doctor_update** — 诊断 + 自更新 + audit.json 读取
10. **templates** — 5 个 agent template（claude/fast/deep/admin/squad），fast/deep/admin/squad 各带 CLAUDE.md + skills/
11. **tests** — 3 层测试（unit/e2e/pre_release）

## 决策 & 跳过

- E2E `tests/e2e -m e2e` 在 collect 阶段因 env spin-up 慢被 5 分钟 timeout 中断。建议 CI `--timeout 600`。
- Pre-release walkthrough 非自动化，用户真机验收已过（见 `e2e-reports/report-v6-finalize-001.md`）。

## 历史 artifacts 清理

- V3/V4/V5 eval-docs / test-plans / code-diffs / test-diffs → 已删
- 保留 V6 finalize evidence: eval-doc-012 + code-diff-v6-finalize-phase{1-7} + e2e-report-v6-finalize-001
- registry.json 重建 version=2

## 下一步

- Stage 4: 修 CS 4 个 E2E（CSAT + help_request lifecycle V6 refactor 后未同步）
- Stage 5: 3 遍 ralph-loop 稳定态
