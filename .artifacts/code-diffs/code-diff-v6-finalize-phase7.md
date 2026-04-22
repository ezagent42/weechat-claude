---
type: code-diff
id: code-diff-v6-finalize-phase7
phase: 7
trigger: pre-release-observation-2026-04-21
status: completed
date: "2026-04-21"
section: 卡片用户体验修正
title: "bridge-to-bridge event 转发 + 卡片 title 用群名 + takeover 态释放按钮"
---

# Phase 7 · 卡片 UX 修正

## 触发

pre-release 实跑发现 2 个问题：

1. **卡片 title 显示 conv-001 而非飞书群名**：phase 5 虽然实现了 `chat_info` 事件机制，但 router 的 `forward_inbound_ws` EVENT 分支**只 broadcast 给 plugin**，**没调 `ws_server.broadcast`** → squad bridge 永远收不到 customer bridge 发的 `chat_info`。
2. **点"接管"无按钮反馈 + 没有"释放"按钮**：renderer 的 action button 固定是"接管 / 结案"，不随 mode 切换；takeover 模式下也显"接管"，operator 看不出当前状态 + 没法一键释放。

## 改动

### Fix 1a · `router.forward_inbound_ws` EVENT 路径补 `ws_server.broadcast`

`zchat-channel-server/src/channel_server/router.py`：
```python
elif msg_type == ws_messages.WSType.EVENT:
    await self._registry.broadcast_event(msg)  # 已有：plugin 订阅
    await self._ws.broadcast(msg)              # 新增：转发给其它 bridge
```

支持 supervise 场景的 bridge↔bridge 事件通信（如 customer 发 `chat_info` → squad 接收缓存 chat_name）。sender bridge 会收到自己的 event 回来，但其 `_on_bridge_event` 已有 own/supervised 过滤，不会重复处理。

### Fix 1b · `feishu_renderer.build_conv_card` title 简化

```python
# 旧: f"对话 {chat_name} · {conversation_id} · {state_label}"  —— 永远有 conv_id
# 新:
display_name = chat_name or conversation_id
title = f"对话 {display_name} · {state_label}"
```

有群名仅显群名（用户面友好）；无群名（timing race / get_chat_info 失败）fallback conv_id。

### Fix 1c · `chat_info` 延到达时回填 + refresh card

`bridge._handle_sys_event` 的 `chat_info` 分支：当 thread/card 已经先建（客户消息先到、chat_info 后到的 race），回填 `thread.metadata["chat_name"]` + `update_card` 刷新 title。

`bridge._handle_supervised_message` 首次建 ConvThread 时 `metadata={"chat_name": chat_name}`，后续 `on_mode_changed` / `_supervise_help_requested` 等刷新卡片沿用，不需每次重查缓存。

### Fix 2 · `build_conv_card` 按 mode 切换 action buttons

`zchat-channel-server/src/feishu_bridge/feishu_renderer.py`：
```python
if state != "closed":
    if mode == "takeover":
        actions = [
            {"text": "释放", "value": {"action": "release", ...}},
            {"text": "结案", "value": {"action": "resolve", ...}},
        ]
    else:
        actions = [
            {"text": "接管", "value": {"action": "hijack", ...}},
            {"text": "结案", "value": {"action": "resolve", ...}},
        ]
    elements.append({"tag": "action", "actions": actions})
```

数据流已就绪（bridge `_on_card_action` 把 `action` 值拼成 `/{action}` 发 WS message；mode plugin `handles_commands` 含 `release`）。按钮点击 → `/release` 命令 → mode_changed to=copilot → `_handle_mode_changed` → `on_mode_changed` → `update_card` 刷新按钮回"接管"。

## 死代码

无。

## 测试

| Suite | Before | After |
|---|---|---|
| zchat-channel-server unit | 183 | 183 |
| zchat CLI unit | 325 | 325 |

无新增测试，行为变化主要是用户面 UX + 数据路径打通（既有测试未覆盖 bridge↔bridge event 转发；该路径将在 pre-release 实跑中验证）。

## 关联

- 上游：e2e-report-v6-finalize-001 + code-diff-phase6
- 触发：pre-release 实跑 2026-04-21 15:47-15:55 bridge-squad.log / bridge-customer.log / cs.log

## 需要 user 操作

重启相关进程让新代码生效：
```bash
uv run zchat shutdown
zellij delete-session zchat-prod --force 2>/dev/null
uv run zchat up
```

再测 TC-PR-2.3 (squad 监管卡片) + TC-PR-2.5b (/hijack /release)：
- 卡片 title 应是"对话 cs-customer · 进行中"
- 点接管 → mode_changed to=takeover → 卡片 title "对话 cs-customer · 进行中" + mode 标"人工接管" + 按钮变"释放 / 结案"
- 点释放 → mode_changed to=copilot → 按钮变回"接管 / 结案"
