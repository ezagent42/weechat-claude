# V3 架构审计结论（修正版）

日期: 2026-04-17

## 基础设施原语

```
Project  → 工作空间配置（IRC server + agent 模板 + routing 配置）
Channel  → IRC 频道（一个群一个 channel）
Agent    → Claude Code 实例（连接到 channel，有独立 soul.md）
```

**不使用 Customer 作为原语**——Customer 是业务概念，由 Bridge adapter 赋予。

## 命令分类（修正）

| 命令 | 分类 | 理由 | 位置 |
|------|------|------|------|
| /dispatch agent channel | **基础设施** | agent 加入 channel | channel-server |
| /hijack | **基础设施** | mode 切换 | channel-server |
| /release | **基础设施** | mode 切换 | channel-server |
| /copilot | **基础设施** | mode 切换 | channel-server |
| /resolve | **基础设施** | 关闭 conversation | channel-server |
| /abandon | **基础设施** | 关闭 conversation（无 CSAT） | channel-server |
| /status | **业务** | 查看状态 | agent skill |
| /review | **业务** | 查看统计 | agent skill |
| /assign /reassign /squad | **业务** | squad 管理 | agent skill |

## 配置分层

```
routing.toml（业务配置）：
  default_agents = ["fast-agent"]          ← 新 conversation 自动 dispatch 谁
  escalation_chain = ["deep-agent"]        ← 升级时按什么顺序
  available_agents = ["fast-agent", "deep-agent"]  ← 白名单（基础设施）

soul.md（业务指令，per-agent）：
  角色定义、沟通风格、行为规则
  存在于 agent workspace，每个实例独立

templates/claude/（基础设施模板）：
  start.sh        ← 启动脚本
  .env.example     ← 环境变量
  template.toml    ← 模板配置
```

## 三个仓库审计

### zchat-protocol（2 处清理）

| 文件 | 动作 |
|------|------|
| event.py | 删除 `SLA_BREACH`, `SQUAD_ASSIGNED`, `SQUAD_REASSIGNED` |
| commands.py | 保留 hijack/release/copilot/resolve/dispatch/abandon；移除 status/review/assign/reassign/squad |

### zchat-channel-server（4 处重构）

| 文件 | 动作 |
|------|------|
| engine/command_handler.py | 保留基础设施命令（hijack/release/copilot/resolve/dispatch/abandon）；移除业务命令（status/review/assign/reassign/squad → agent skill） |
| feishu_bridge/bridge.py | 移除 auto-hijack（注释已关）；简化为纯协议转换 |
| feishu_bridge/visibility_router.py | 保持当前拆分（visibility_router + feishu_renderer） |
| plugins/sla_app.py | SLA 时长已可配置（环境变量）；SLA 策略移到 routing.toml 或 skill 配置 |

### zchat 主库（核心改动）

| 改动 | 说明 |
|------|------|
| CLI: `zchat channel create/list/delete` | 新增 channel 管理命令 |
| CLI: `zchat agent join agent channel` | 新增 agent 加入 channel 命令 |
| agent_manager.py | create() 支持指定 channels；per-channel agent 实例 |
| irc_manager.py | 动态 channel 解析 |
| templates/ | soul.md 支持 per-agent-type 差异化（fast vs deep vs admin vs squad） |

## Agent 模板体系

```
内置模板（zchat/cli/templates/）：
  claude/          ← 通用 agent 模板
    soul.md        ← 默认业务指令
    start.sh       ← 启动脚本
  
用户自定义（~/.zchat/templates/）：
  fast-agent/      ← 快速应答 agent
    soul.md        ← "简单问题直接答，复杂问题占位"
  deep-agent/      ← 深度分析 agent
    soul.md        ← "接收委托，深度分析，reply(edit_of=)"
  admin-agent/     ← 管理 agent（未来）
    soul.md        ← admin skill 指令
  squad-agent/     ← 分队 agent（未来）
    soul.md        ← squad skill 指令
```

每种 agent type 有独立的 soul.md 定义行为。启动时复制到 agent workspace。

## 执行计划

### Phase 1: 协议清理 + 命令修正
1. zchat-protocol: event.py 删业务事件
2. zchat-protocol: commands.py 调整（保留 dispatch，移除 status/review/assign/reassign/squad）
3. channel-server: command_handler.py 移除业务命令处理

### Phase 2: Channel 管理
4. zchat CLI: channel create/list/delete 命令
5. zchat CLI: agent join/leave channel 命令
6. channel-server: 统一 channel 管理 API

### Phase 3: Agent 模板差异化
7. templates/: fast-agent / deep-agent / admin-agent / squad-agent 独立 soul.md
8. 运行时 per-channel agent 实例

### Phase 4: Bridge 清理
9. bridge.py: 简化为纯协议转换
10. 卡片/thread 路由修正
