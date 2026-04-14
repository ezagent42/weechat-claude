---
name: "project-discussion-channel-server"
description: "Project knowledge Q&A skill for zchat-channel-server (MCP bridge IRC <-> Claude Code). Provides evidence-backed answers about server architecture, IRC event handling, MCP tool registration, message chunking, sys message protocol, slash commands, and instructions template. Trigger this skill for any channel-server question — code structure, module relationships, test status, E2E pipeline info (for Skill 3), and bug triage (Phase 8 feedback routing). Also trigger when discussing cs-* artifacts, debugging IRC-MCP bridge issues, or querying test coverage gaps in channel-server."
---

# zchat-channel-server 项目知识库

> 由 Skill 0 (project-builder) 于 2026-04-14 自动生成。
> 这是一个**行为引擎**——指导如何查询和回答，数据存储在 `.artifacts/` 中。

## 项目概览

- **项目根目录**：zchat-channel-server/（zchat 的 git submodule）
- **语言/框架**：Python 3.13 + MCP (mcp[cli]) + irc library + asyncio
- **测试框架**：pytest 9.0.2 + pytest-asyncio (asyncio_mode=auto)
- **模块数**：2 (cs_server + cs_message)
- **Artifact 空间**：.artifacts/（zchat 根目录，所有 cs-* 前缀 artifact）
- **Skill 6 可用**：是（plugin cache path）
- **Artifact ID 前缀**：`cs-`（所有 channel-server artifact 必须以此开头）

## 问答流程

被问到 channel-server 相关问题时，按以下步骤回答。目标是**每个回答都有实证**，不编造。

### Step 0: 检测更新（自动刷新）

每次回答前，检查是否有新的代码变更需要刷新索引：

1. 查询 `.artifacts/` 中 ID 以 `cs-` 开头的 `code-diff` 和 `e2e-report`，找出比 2026-04-14 更新的条目
2. 如果有新的 cs-* code-diff：
   - 读取 diff 内容，识别受影响的模块（cs_server 或 cs_message）
   - 对受影响的模块：**重新读取源文件**（更新 file:line 引用）
   - 对受影响的模块：**重新运行 test-runner**（更新基线结果）
   - 用新数据回答，而不是依赖过时的索引
3. 如果有新的 cs-* e2e-report：
   - 读取 report 了解哪些测试新增/修复
   - 更新覆盖认知

如果没有新 artifact，跳过此步骤直接进入 Step 1。

**异常处理**：如果索引中的文件路径不存在（文件已移动/重命名），重新扫描 `zchat-channel-server/` 下的 `.py` 文件查找。

### Step 1: 解析问题 -> 定位模块

查阅下方"模块索引"，找到问题涉及的模块：
- **IRC 连接、MCP server、事件处理、sys 消息、slash 命令** → cs_server
- **@mention 检测、消息分片、IRC 字符限制** → cs_message

如果不确定涉及哪个模块，查"用户流程->模块映射"表。

### Step 2: 读取代码

根据索引中的文件路径，用 Read 工具读取**当前**代码。引用具体的 file:line。

关键文件路径：
- `zchat-channel-server/server.py` — 主 MCP server（321 行）
- `zchat-channel-server/message.py` — 消息工具（63 行）

### Step 3: 跑测试验证

运行对应的 test-runner 脚本，捕获**当前**输出作为证据：

```bash
bash .claude/skills/project-discussion-channel-server/scripts/test-cs_server.sh
bash .claude/skills/project-discussion-channel-server/scripts/test-cs_message.sh
bash .claude/skills/project-discussion-channel-server/scripts/test-all.sh
```

### Step 4: 查询已有知识

查询 `.artifacts/` 中 `cs-*` 前缀的相关 artifact：
- 被驳回的 eval-doc（status=archived）——已知边界/FAQ
- e2e-report——最近的测试结果和修复历史
- code-diff——最近的代码变更
- coverage-matrix——测试覆盖现状

```bash
SKILL6=/home/yaosh/.claude/plugins/cache/ezagent42/dev-loop-skills/0.1.0/skills/skill-6-artifact-registry/scripts
bash "$SKILL6/query.sh" --project-root /home/yaosh/projects/zchat --type eval-doc --status archived
```

### Step 5: 组织回答

回答格式：
1. 直接回答问题
2. 附上证据：file:line 引用 + 测试输出
3. 如果在 `.artifacts/` 中找到相关的被驳回 eval-doc，引用它作为已知边界

如果无法确认某个断言，标注为 `[unverified]` 而不是猜测。

### Step 6: 分流判断（自然延伸，非独立模式）

如果本次讨论涉及 `.artifacts/` 中的 cs-* eval-doc 或 issue（比如用户带着一个问题来讨论"这是不是 bug"），在 Step 5 回答后继续：

1. **明确提出分析结论**：基于代码证据和测试结果，给出判断
2. **询问人是否确认**结论
3. **人确认后执行对应操作**：

**结论是 bug**：
- Issue 保持 open
- 告知用户：eval-doc 将进入 Phase 3（Skill 2 生成 test-plan）

**结论不是 bug**：
```bash
SKILL6=/home/yaosh/.claude/plugins/cache/ezagent42/dev-loop-skills/0.1.0/skills/skill-6-artifact-registry/scripts
bash "$SKILL6/update-status.sh" --project-root /home/yaosh/projects/zchat --id <cs-eval-doc-id> --status archived
```
同时在 eval-doc 的 frontmatter 中追加：
```yaml
rejection_reason: "<具体原因，引用代码证据>"
rejected_at: "2026-04-14"
```

如果讨论**不涉及**任何 eval-doc/issue，Step 5 回答完即结束。

---

## 自我演进

### 动态层：自动刷新（Step 0）

- **新 cs-* code-diff** -> 重新读取受影响模块的源文件 + 重新跑 test-runner
- **新 cs-* e2e-report** -> 更新覆盖认知
- **文件路径失效** -> 扫描 `zchat-channel-server/` 重建索引

### 知识层：artifact 积累

- **驳回结论** -> eval-doc archived + rejection_reason
- **Bug 修复历史** -> eval-doc -> test-plan -> e2e-report 链条
- **覆盖变化** -> 新 e2e-report 更新 coverage-matrix

### 何时需要重新 bootstrap

- 大规模重构（server.py 拆分为多个模块）
- 新增全新的 Python 模块
- 测试框架更换

---

## 模块索引

| 模块 | 路径 | 职责 | 测试命令 | 基线结果 | 用户流程 |
|------|------|------|---------|---------|---------|
| cs_server | `zchat-channel-server/server.py` + `commands/` + `instructions.md` | MCP server 桥接 IRC <-> Claude Code：IRC 连接、事件处理、MCP tool 注册、sys 消息分发、指令模板 | `cd zchat-channel-server && uv run pytest tests/unit/test_legacy.py -v` | 5/5 passed | MCP启动, @mention通知, 私信通知, sys消息, reply tool, join tool, slash commands |
| cs_message | `zchat-channel-server/message.py` | IRC 消息工具：@mention 检测/清理、消息分 chunk（UTF-8 字节安全，CJK 兼容） | `cd zchat-channel-server && uv run pytest tests/unit/test_message.py -v` | 7/7 passed | mention检测, 消息分片 |

## 详细模块描述

详见 `references/module-details.md`（从 `.artifacts/bootstrap/module-reports/cs_*.json` 汇总生成）。

### cs_server 摘要

MCP server（server.py:290 `main()`）通过 `setup_irc()` (server.py:76) 在守护线程中运行 IRC reactor，`asyncio.Queue` 桥接到 MCP async 循环。`poll_irc_queue()` (server.py:63) 消费消息并通过 `inject_message()` (server.py:43) 以 `notifications/claude/channel` 方法注入 Claude Code。注册两个 MCP tool：`reply` (server.py:270) 和 `join_channel` (server.py:280)。

### cs_message 摘要

纯工具模块，无外部依赖。`detect_mention()` (message.py:12) 检测 @agent 提及，`clean_mention()` (message.py:17) 清理，`chunk_message()` (message.py:27) 按 390 字节上限分片（预留 IRC header 空间），支持 CJK 多字节字符。

## 用户流程 -> 模块映射

| 用户流程 | 操作步骤 | 涉及模块 | 入口 file:line | E2E 覆盖 |
|---------|---------|---------|---------------|---------|
| MCP server 启动并连接 IRC | `entry_point()` -> `main()` -> `setup_irc()` | cs_server | server.py:315 | ❌ |
| Channel @mention -> Claude 通知 | IRC pubmsg -> `on_pubmsg()` -> `detect_mention()` -> queue -> `inject_message()` | cs_server, cs_message | server.py:112 | ❌ |
| Private message -> Claude 通知 | IRC privmsg -> `on_privmsg()` -> queue -> `inject_message()` | cs_server | server.py:133 | ❌ |
| 系统消息处理 (stop/join/status) | IRC privmsg -> `decode_sys_from_irc()` -> `_handle_sys_message()` | cs_server | server.py:186 | ❌ |
| MCP tool: reply (发送 IRC 消息) | Claude calls reply -> `_handle_reply()` -> `chunk_message()` -> `privmsg()` | cs_server, cs_message | server.py:270 | ❌ |
| MCP tool: join_channel | Claude calls join_channel -> `_handle_join_channel()` -> `connection.join()` | cs_server | server.py:280 | ❌ |
| /zchat:broadcast 广播消息 | User invokes slash command -> calls reply for each channel | cs_server | commands/broadcast.md:1 | ❌ |
| /zchat:dm 私聊消息 | User invokes slash command -> calls reply with user nick | cs_server | commands/dm.md:1 | ❌ |

## 测试 Pipeline 信息

供 Skill 3 (test-code-writer) 查询，了解如何在此项目中追加 E2E 测试用例。

- **测试框架**：pytest 9.0.2 + pytest-asyncio (asyncio_mode=auto)
- **E2E 测试目录**：zchat-channel-server/tests/e2e/（当前为空，仅 __init__.py）
- **E2E conftest 位置**：(不存在，需要创建)
- **已有 fixture 列表**：(无)
- **fixture 模式**：channel-server E2E 测试需要 IRC server (ergo) + MCP stdio 模拟。建议参考 zchat 主库的 `tests/e2e/conftest.py` 模式：session-scoped fixture
- **测试命名规范**：`test_{action}_{target}`（如 test_sys_message_irc_roundtrip, test_detect_mention）
- **证据采集工具**：需要 IRC 客户端连接验证消息到达（参考 zchat 主库的 IrcProbe）
- **证据采集方式**：IRC PRIVMSG 验证消息到达 + MCP stdio 输出捕获
- **E2E 标记/marker**：`@pytest.mark.e2e`（已在 pytest.ini 注册）
- **运行 E2E 的命令**：`cd zchat-channel-server && uv run pytest tests/e2e/ -v -m e2e`
- **关键外部依赖**：irc>=20.0, mcp[cli]>=1.2.0, zchat-protocol>=0.1.0

## Test Runners

| 脚本 | 模块 | 命令 | 基线结果 |
|------|------|------|---------|
| scripts/test-cs_server.sh | cs_server | `cd zchat-channel-server && uv run pytest tests/unit/test_legacy.py -v` | 5/5 passed |
| scripts/test-cs_message.sh | cs_message | `cd zchat-channel-server && uv run pytest tests/unit/test_message.py -v` | 7/7 passed |
| scripts/test-all.sh | (全局) | `cd zchat-channel-server && uv run pytest tests/unit/ -v` | 12/12 passed |

## Artifact 交互

所有 channel-server artifact ID 以 `cs-` 开头。

查询 artifact：
```bash
SKILL6=/home/yaosh/.claude/plugins/cache/ezagent42/dev-loop-skills/0.1.0/skills/skill-6-artifact-registry/scripts
bash "$SKILL6/query.sh" --project-root /home/yaosh/projects/zchat --type eval-doc --status archived
```

注册新 artifact：
```bash
bash "$SKILL6/register.sh" --project-root /home/yaosh/projects/zchat \
  --type eval-doc --name "cs-eval-{phase}" --producer skill-1 \
  --path .artifacts/eval-docs/cs-eval-{phase}.md --status open
```

更新状态：
```bash
bash "$SKILL6/update-status.sh" --project-root /home/yaosh/projects/zchat \
  --id cs-eval-{phase} --status archived
```

关联 artifact：
```bash
bash "$SKILL6/link.sh" --project-root /home/yaosh/projects/zchat \
  --from cs-eval-{phase} --to cs-plan-{phase}
```

### Artifact 命名约定

| Phase | eval-doc | test-plan | code-diff | e2e-report |
|-------|----------|-----------|-----------|------------|
| Phase 1 | cs-eval-protocol | cs-plan-protocol | cs-diff-protocol | cs-report-protocol |
| Phase 2 | cs-eval-engine | cs-plan-engine | cs-diff-engine | cs-report-engine |
| Phase 3 | cs-eval-bridge | cs-plan-bridge | cs-diff-bridge | cs-report-bridge |
| Phase 4 | cs-eval-server | cs-plan-server | cs-diff-server | cs-report-server |
| Phase 5 | cs-eval-cli | cs-plan-cli | cs-diff-cli | cs-report-cli |

## 自验证记录

Skill 1 生成后，所有 test-runner 已运行并与基线比对通过。

| test-runner | 基线结果 | 验证结果 | 匹配 |
|-------------|---------|---------|------|
| test-cs_server.sh | 5/5 passed | 5/5 passed (exit 0) | ✅ |
| test-cs_message.sh | 7/7 passed | 7/7 passed (exit 0) | ✅ |
| test-all.sh | 12/12 passed | 12/12 passed (exit 0) | ✅ |

验证时间：2026-04-14，全部 3 个 test-runner 已运行并通过。

## 环境依赖

| 依赖 | 状态 | 说明 |
|------|------|------|
| ergo IRC server | 必需 (E2E) | E2E 测试需要 IRC 连接，unit test 不需要 |
| uv >=0.7 | 必需 | 依赖管理 + 测试运行 |
| Python >=3.11 | 必需 | pyproject.toml 要求 |
| mcp[cli] >=1.2.0 | 必需 | MCP server 框架 |
| irc >=20.0 | 必需 | IRC 客户端库 |
| zchat-protocol >=0.1.0 | 必需 | 协议规范（editable path ../zchat-protocol） |
| tmux | 可选 | channel-server 不直接依赖，但 zchat 主库 E2E 需要 |
| asciinema | 可选 | pre-release 录制 |
| docker | 可选 | 当前无测试依赖 |
