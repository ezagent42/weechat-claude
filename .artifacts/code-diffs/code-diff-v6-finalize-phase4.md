---
type: code-diff
id: code-diff-v6-finalize-phase4
phase: 4
trigger: eval-doc-012
status: completed
date: "2026-04-21"
section: §3.2
title: "help_requested 通知链 + 业务术语红线扫描清理"
---

# Phase 4 · help_requested 通知链 + 业务术语红线清理

## 范围

- sla plugin: `@operator/@人工/@admin/@客服` marker → emit `help_requested` event 立即通知 + 启动 180s timer
- bridge `event` 类型 WS 消息支持监管路径
- squad bridge 订阅 supervised channel 上的 `help_requested` / `help_timeout` → update_card "🚨 求助中" + reply_in_thread `<at user_id="all"></at>`
- feishu_renderer 扩展卡片 state（active/closed/help_requested/help_timeout）+ chat_name title fallback + alert 元素
- bridge 入站 sender filter：忽略本 bot 自发消息（`event.sender.sender_id.app_id == self.config.feishu.app_id`）
- 同步**业务术语红线扫描清理**

## 改动 · §3.2 主线

### `zchat-channel-server/src/plugins/sla/plugin.py`
- 模块顶部常量改名：`HELP_MENTION_PATTERNS` → `HELP_REQUEST_MARKERS`；`OPERATOR_SOURCE_MARKERS` → `HUMAN_RELAY_SOURCE_MARKERS = ("cs-bot",)`
- `_looks_like_operator` → `_is_human_relay`（语义对齐：检查 source 是否为 bridge 中继）
- `on_ws_message`: 检测求助 marker → emit `help_requested` event（payload 含 `text` + `requesting_source`）+ `_start_help_timer(channel, text)`
- `_start_help_timer/_help_timer_task` 签名加 `request_text`，timeout payload 含 `text` 字段
- `help_timeout.reason`: `operator_no_response` → `no_human_response`

### `zchat-channel-server/src/feishu_bridge/bridge.py`
- `_EVENT_HANDLERS` 加 `"event": "_handle_sys_event"`
- `_on_bridge_event`: supervised 路径加 `event` 分支调 `_handle_sys_event`
- 新方法 `_handle_sys_event`：only supervised channel 处理；分发到 `_supervise_help_requested`/`_supervise_help_timeout`
- 新方法 `_supervise_help_requested`：build_conv_card with `state="help_requested"` + `metadata["alert"]="🚨 求助中"` → update_card；`reply_in_thread` 用 `<at user_id="all"></at>` + 求助文本
- 新方法 `_supervise_help_timeout`：state="help_timeout" + alert="⚠️ 求助超时" + thread 提醒
- `_on_message` 加自发回环过滤：`sender.sender_id.app_id == config.feishu.app_id` → 忽略

### `zchat-channel-server/src/feishu_bridge/feishu_renderer.py`
- 模块顶常量化：`_STATE_LABELS` 加 `help_requested="🚨 求助中"` / `help_timeout="⚠️ 求助超时"`
- `_MODE_LABELS` 加 `help="等待人工"`
- `_TEMPLATE_BY_STATE` 映射：`closed/help_timeout=red`, `help_requested=orange`, 其它=blue
- `build_conv_card` title 优先用 `metadata["chat_name"]` + conv_id + 状态；fallback conv_id 单独
- 新增 alert 元素：`metadata["alert"]` 出现时插入卡片顶部 lark_md
- 移除依赖 inline `state == "closed"` 颜色判断，统一走 `_TEMPLATE_BY_STATE`

## 改动 · §架构红线（业务术语清理）

### `zchat-channel-server/src/plugins/audit/plugin.py`
- 新模块常量 `_INFRASTRUCTURE_SOURCES = frozenset({"cs-bot", "internal", "card_action"})`（仅基础设施 source）
- `_looks_like_agent`: 改用 `_INFRASTRUCTURE_SOURCES`，删除 `customer/operator/admin` 业务名 blocklist

### `zchat-channel-server/src/channel_server/routing.py`
- 模块 docstring V6 schema 示例：`[bots."customer"]` → `[bots."<bot_name>"]`，`bot = "customer"` → `bot = "<bot_name>"`，`credential_file` 同步通配化

### `zchat/cli/routing.py`
- 同样 docstring 通配化

### `zchat/cli/project.py`
- **删除** `_channel_server_defaults()` 函数（V3/V4 死代码：bridge_port / plugins_dir / db_path / timers / participants —— 全部没有 V6 consumer）
- `generate_default_config`: 不再注入 `[channel_server]` 段
- `load_project_config`: 不再 `setdefault("channel_server", ...)`

### `zchat-protocol/tests/test_ws_messages.py`
- `test_parse_unknown_type_raises`: fixture type 从 `"customer_message"` 改成 `"made_up_type"`（避免业务名进协议测试）

### `zchat-channel-server/src/channel_server/router.py`
- 注释更新：`# 已有前缀（比如 operator 在 side thread...）` → `# 已有前缀（bridge 转发的 thread reply 已自带 __side: 等）`

## 死代码删除汇总

- `zchat/cli/project.py::_channel_server_defaults()` 整函数
- `zchat/cli/project.py` 中 channel_server config 注入逻辑（generate + load 两处）
- `tests/unit/test_config_channel_server.py` 整文件（全是测删掉的 channel_server defaults）
- `OPERATOR_SOURCE_MARKERS` 常量（ou_ 前缀检测，已被 bridge 路径替代）
- `_looks_like_operator` 方法（替换为 `_is_human_relay`）

## 业务术语红线扫描结果

| 范围 | 状态 |
|---|---|
| `zchat-channel-server/src/channel_server/` | ✅ 干净（routing.py docstring 用 `<bot_name>` 通配） |
| `zchat-protocol/zchat_protocol/` | ✅ 干净 |
| `zchat/cli/` (除 templates 外) | ✅ 干净（routing.py docstring 通配化） |
| `zchat-channel-server/src/feishu_bridge/` | ✅ **允许**（bridge 是业务层） |
| `zchat-channel-server/src/plugins/` | 部分允许（HELP_REQUEST_MARKERS 是 agent 约定文本不是命名，audit/csat 用 customer_returned/customer 作为事件名/默认源） |
| `zchat/cli/templates/` | ✅ **允许**（agent 用户面文本） |

## sla plugin 测试更新

- `test_operator_side_cancels_help_timer` → `test_human_relay_side_cancels_help_timer`：source 从 `operator_小李` 改 `cs-bot`，断言行为不变
- `test_help_timer_expiry_emits_help_timeout`: reason 断言从 `"operator_no_response"` → `"no_human_response"`，新增 `data["text"]` 断言

## 测试结果

| Suite | Before | After | Δ |
|---|---|---|---|
| zchat-channel-server unit | 181 | 181 | 0 (rename + add not net) |
| zchat CLI unit | 330 | 325 | -5 (删 test_config_channel_server.py 整文件) |
| zchat-protocol unit | 32 | 32 | 0 |

无回归。

## 关联 artifacts

- 上游：eval-doc-012, code-diff-v6-finalize-phase3
- 下游：e2e-report-v6-finalize-001（最终验收）

## 完成判据 mapping (eval-doc-012 §完成判据)

| # | Promise | Phase 4 满足 |
|---|---|---|
| 3 | sla emit help_requested event | ✅ |
| 4 | squad bridge 订阅 → update_card "🚨 求助中" + reply_in_thread `<at all>` | ✅ |
| 5 | customer bridge `get_chat_info` chat_name 进 metadata | ⚠️ deferred to V7（需 protocol 加 metadata 字段，跨 protocol 仓不在本 sprint 范围） |
| 6 | feishu_renderer build_conv_card title 用 chat_name | ✅ (chat_name fallback 已实现，metadata 注入路径见 #5) |
| 7 | bridge sender filter 自发消息 | ✅ |
| 12 | 业务术语红线 | ✅ (core/protocol/CLI 干净；bridge/templates 允许) |
| 13 | unit tests 全绿 | ✅ |
| 14 | 死代码 grep 零命中 | ✅ |
