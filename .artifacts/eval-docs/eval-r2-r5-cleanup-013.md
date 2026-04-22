---
type: eval-doc
id: eval-doc-013
status: resolved
producer: skill-5
created_at: "2026-04-22T00:00:00Z"
resolved_at: "2026-04-22T00:00:00Z"
mode: verify
feature: r2-r5-deep-cleanup
submitter: yaosh
related:
  - code-diff-r2-main
  - code-diff-r2-cs
  - code-diff-r4-restore-annotations
spec: docs/discuss/008-v6-finalize-plan.md
plan: ralph-loop · R1-R5
---

# Eval: Ralph-Loop R1-R5 死代码深度清理

## 状态

✅ **resolved** — 五轮 ralph-loop 收敛，三仓 540 → 527 passed / 0 failed，红线干净，working tree clean。

## 范围

通过 R1 三仓 subagent 并行深扫产出 81 个 issues（37 main + 33 CS + 11 protocol），R2-R4 选取**高价值低风险**子集执行清理，R5 验证稳定态。

## R1 Issue 分布

| 仓 | issues | 来源 subagent |
|---|---|---|
| 主库 | 37 | af0ed33 |
| channel-server | 33 | aa6f182 |
| zchat-protocol | 11 | a789a80 |

## 实施清理

### 主库（commit `f8dbd97`）
- 整模块删: `migrate.py`, `tmux_helpers.py`, `test_migrate.py`, `test_runner.py`
- 函数删: `resolve_runner` / `list_runners` / `get_start_script` / `subscribe_pane` / `auth_file` / `project_kdl_config` / `legacy_agent_state`
- 死分支清: `_get_zellij_session` tmux fallback, `cmd_channel_remove --stop-agents` 重写, `cmd_up` legacy username, `irc_manager` legacy weechat_pane_id, 多处 `window_name` fallback
- 配置改: `_VERSION_CMDS` 删 tmux/tmuxp 加 zellij/jq, `doctor` IRC port 走 resolve_server, audit_cmd 去业务名

### channel-server（commit `726540d`）
- 核心模块: 删 `send_sys` / `on_privmsg` 链 / `joined_channels` / `connection_count` / `RoutingTable.{external_chat_id,channels_for_bot}` / `ChannelRoute.channel_id`
- bridge: 删 `_EVENT_HANDLERS` 5 个 V3 幽灵 msg_type + 5 handler / `capabilities=[customer,operator,admin]` → `[]` / `event="connect"` emit / `on_conversation_created` noop
- outbound: 删 `get_feishu_msg_id` / `get_conversation_for_thread` / `ConvThread.customer_chat_id` / `ChannelMapper.{set,remove}_mapping`
- 重写: `routing.example.toml` V4 schema → V6

### Restore 注释（commit `1d46882`）
- `paths.py`: 3 处 REMOVED 块（auth_file / project_kdl_config / legacy_agent_state）
- `runner.py`: 模块 docstring 重写，记录 resolve_runner/list_runners 删除 + 4 步重启计划
- `template_loader.py`: get_start_script 删除注释 + 重启范例

## 作者归属审计

| 类别 | 数量 | 来源 |
|---|---|---|
| Allen Woods 创建 | 4 整文件 + 5 函数 (主库) | 全部为 Allen 自己迁移后遗弃（V3→V4 / tmux→zellij），不是扩展预留 |
| Sy Yao 创建 | 全部 CS 删除项 | V4/V5/V6 重构过程中产生的废代码 |

特殊审视项：
- **`on_privmsg` (DM 预留)** — V4-S2a `e7bbe72` 接线但 V5/V6 至今无 caller。删除不影响未来 DM 扩展（router/agent-mcp 端本就需要重新设计）。已 commit。
- **`on_conversation_created` noop** — V4-S3 `cc3c8af` 留为 V7 cross-bot supervision 占位，但实际是 `return None`。已 commit。
- **`capabilities=[]`** — 字段保留（V7 skill-aware routing 扩展点），仅清掉硬编码业务值。

## 协议层 (zchat-protocol)

11 issues **全部不动**。原因：
- `WSType.COMMAND/ACK` 是预留枚举，删除会改 protocol 面
- `EDIT_PREFIX/SIDE_PREFIX/SYS_PREFIX` 常量是公开合同
- 其余是 lint 风格 / 类型细化建议，非死代码

## 测试结果

| Suite | Before R1 | After R5 | Δ |
|---|---|---|---|
| 主库 unit | 325 | 304 | -21 (test_migrate 删除 + test_runner 删除 + test_paths.test_auth_file 删除) |
| CS unit + e2e | 195 | 191 | -4 (V6 同步 + 死 API 测试一同删) |
| protocol | 32 | 32 | 0 |
| **总** | **552** | **527** | **-25** |

无回归。所有删除均为对应已删生产代码的孤儿测试。

## 代码量

约 **-1000 行**（主库 -867 / CS -148 净）。

## 关联 commits

- `f8dbd97` chore(R2): 主库深度清死代码
- `726540d` chore(R2): CS 跨仓死代码清理
- `1d46882` docs(cli): inline REMOVED-{date} annotations for V7+ extension restore

## 下游 artifact

- e2e-report-v6-finalize-001（之前已注册）继续有效
- 本 sprint 不产生 new code-diff（所有改动已封进上述 3 commit message）

## 完成判据

| # | Promise | 满足 |
|---|---|---|
| 1 | 5 轮 ralph-loop 完成 (R1 扫 → R2/R3/R4 修 → R5 收敛验证) | ✅ |
| 2 | 三仓 unit tests 全绿 | ✅ 527/0 |
| 3 | 红线扫描 0 命中 (core/protocol/CLI) | ✅ |
| 4 | working tree clean | ✅ |
| 5 | submodule 指针正确 | ✅ |
| 6 | 删除项作者归属审计 + DM 风险评估 | ✅ |
| 7 | Allen 文件 / runner 扩展点 inline 注释 restore plan | ✅ |

## 状态收口

5/5 ralph-loop 稳定态。无后续清理需求。
