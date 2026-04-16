# Pre-release 手动测试 Bug 清单

日期: 2026-04-16
测试人: yaosh
环境: WSL2 + ergo 2.18.0 + zchat channel-server test/phase-final-prerelease

---

## Bug 1: 重复回复

**现象**: 客户发一条 "你好"，收到 2-3 条回复。

**根因**: feishu_bridge `_on_message()` 无消息去重。飞书平台延迟重发事件时，同一条消息被处理多次。

**架构层级**: Bridge adapter（feishu_bridge）

**修复方案**: feishu_bridge 加 `message_id` 去重缓存。这是 Bridge adapter 的职责 — 每个渠道适配器自己处理自己平台的消息重发问题。channel-server 不需要知道。

**修复位置**: `feishu_bridge/bridge.py` `_on_message()`

---

## Bug 2: 卡片按钮报错 20067

**现象**: 在 squad 群点击卡片的"接管"或"结案"按钮，飞书返回 20067 错误码。日志: `processor not found, type: card.action.trigger`。

**根因**: 
1. `build_event_handler()` 没有注册 `card.action.trigger` 事件处理器
2. `_on_card_action()` 只处理 CSAT 评分，不处理 hijack/resolve 按钮

**架构层级**: Bridge adapter（feishu_bridge）

**修复方案**: 
- 注册 `card.action.trigger` handler
- 按钮 action.value 中的 `action` 字段区分类型：
  - `action: "hijack"` → 转发为 `operator_command(/hijack)` 到 Bridge API
  - `action: "resolve"` → 转发为 `operator_command(/resolve)` 到 Bridge API
  - 有 `score` 字段 → CSAT 评分（已有逻辑）
- **不在 feishu_bridge 中实现命令逻辑**，只做协议转换 → Bridge API → channel-server CommandHandler 处理

**修复位置**: `feishu_bridge/bridge.py` `build_event_handler()` + 新增 `_on_card_action_trigger()`

---

## Bug 3: SLA 告警不可读

**现象**: admin 群收到 `[系统] [SLA 告警] conv_id=oc_3e33d9eddc980a800c3eefa01c6ca0f7 breach=sla_onboard timeout=3.0s`

**问题**:
1. `conv_id` 是原始 chat_id，不是群名称或客户名字 — 运维看不懂
2. 客户用 `open_id` 标识（`ou_ed51feba...`）— 不知道是谁
3. SLA onboard 3 秒就 breach — 不合理

**架构层级**: 分两层

| 问题 | 层级 | 说明 |
|------|------|------|
| SLA timer 时长 | Plugin（sla_app.py） | 业务配置，应可通过 routing.toml 或环境变量配置 |
| 告警消息格式 | Bridge adapter（feishu_bridge） | 将 conv_id/open_id 翻译为可读名称是 Bridge 的职责 |
| 客户姓名解析 | Bridge adapter（feishu_bridge） | feishu_bridge 在 customer_connect 时用飞书 API 查用户名，填入 metadata |

**channel-server 不应该关心名称解析** — 它只传递 ID 和 metadata。Bridge adapter 负责把 ID 翻译成对应渠道的可读格式。

**修复位置**: 
- `plugins/sla_app.py`: timer 时长可配置
- `feishu_bridge/bridge.py`: customer_connect 时查飞书用户名填入 metadata.customer.name
- `feishu_bridge/visibility_router.py`: 告警消息用 metadata 中的可读名称渲染

---

## Bug 4: Squad thread 缺少客户消息

**现象**: Squad 群的 card thread 只显示 bot 的回复（`[→客户] 你好！请问有什么可以帮到您的？`），看不到客户说了什么。Operator 无法了解完整对话上下文。

**架构层级**: 分两层

| 环节 | 层级 | 说明 |
|------|------|------|
| channel-server 发送 reply 事件 | Engine | reply 事件已包含 visibility，channel-server 不管渲染 |
| 飞书 squad thread 写入 | Bridge adapter | VisibilityRouter 决定往 thread 写什么 |

**修复方案**: 当 feishu_bridge 收到 customer_message 并转发到 Bridge API 后，**同时**往 squad thread 写一条 `[客户] {text}`。

两个可选实现位置：
1. **channel-server**: customer_message 到达后，额外发一条 `reply(visibility=system, text="[客户] xxx")` 到 Bridge — 但这让 channel-server 知道了"squad thread 需要看到客户消息"这个业务需求，**违反基础设施原则**
2. **feishu_bridge**: 在 `_forward_to_bridge()` 转发 customer_message 的同时，直接调 `visibility_router.route(conv_id, {visibility: "system", text: f"[客户] {text}"})` 写入 squad thread — **Bridge adapter 自己决定如何展示**

**推荐方案 2** — Bridge adapter 负责渲染展示，channel-server 不参与。

**修复位置**: `feishu_bridge/bridge.py` `_forward_customer()`

---

## Bug 5: #conv- channel 未创建 + customer_connect 异常中断连接

**现象**: WeeChat 中没有 `#conv-oc_3e33...` channel。channel-server 终端没有任何 customer_connect 相关输出。但 agent 确实收到消息并回复了。

**根因链路**:
1. feishu_bridge 发 `customer_connect` 到 Bridge API
2. `ws_server.py` 的 `_handle_connection` 处理 `customer_connect` → 调 `on_customer_connect` callback
3. `handle_customer_connect()` 中 `irc_transport.join(channel)` **可能抛异常**（或 callback 本身报错）
4. `_handle_connection` 的 line 249-250 **没有 try/except**，异常直接中断 `async for raw in websocket` 循环
5. **WebSocket 连接断开**
6. `bridge_api_client` 自动重连
7. 重连后 `_known_conversations` 已标记，不再发 `customer_connect`，直接发 `customer_message`
8. `customer_message` 处理正常（line 253-254），agent 收到并回复
9. 但 `#conv-` channel **从未成功创建**

**架构层级**: Bridge API 传输层（ws_server.py）+ Engine（command_handler.py）

**修复方案**:
1. `ws_server.py` 所有 callback 调用加 `try/except`，异常记日志但不中断连接
2. `handle_customer_connect` 加 debug print 确认执行路径
3. `irc_transport.join()` 的异常已有 try/except（command_handler.py:184），需确认是否生效

**修复位置**: `bridge_api/ws_server.py` `_handle_connection()`

---

## Bug 6: Zellij session 创建卡住（原 Bug 5）

**现象**: `uv run zchat project use prerelease-test` 卡在 "ergo running" 不动。

**根因**: `zellij.ensure_session()` 用 `subprocess.run(capture_output=True)` 执行 `--new-session-with-layout`，该命令是交互式的会阻塞。

**架构层级**: zchat CLI（zellij.py）

**修复位置**: `zchat/cli/zellij.py` `ensure_session()` — `--new-session-with-layout` 需要后台模式

---

## Bug 7: CHANNEL_PKG_DIR 为空导致 plugin error（原 Bug 6）

**现象**: Claude Code agent tab 显示 "error in plugin"。

**根因**: `_find_channel_pkg_dir()` 在 `uv tool dir` 下找 channel-server 包，但 editable install 不在那个路径。

**架构层级**: zchat CLI（agent_manager.py）

**修复位置**: `zchat/cli/agent_manager.py` `_find_channel_pkg_dir()` — 加 editable install fallback

---

## 架构原则检查

| Bug | 修复是否在正确层级 | 是否耦合业务到基础设施 |
|-----|:--:|:--:|
| 1 重复回复 | ✅ Bridge adapter 去重 | ❌ 不耦合 |
| 2 卡片按钮 | ✅ Bridge adapter 协议转换 | ❌ 不耦合 |
| 3 SLA 不可读 | ✅ Plugin 配置 + Bridge 渲染 | ❌ 不耦合 |
| 4 Thread 缺客户消息 | ✅ Bridge adapter 自己渲染 | ❌ 不耦合（方案 2） |
| 5 #conv- channel 未创建 | ✅ 传输层异常处理 | ❌ 不耦合 |
| 6 Zellij 卡住 | ✅ CLI 修复 | ❌ 不耦合 |
| 7 Plugin error | ✅ CLI 修复 | ❌ 不耦合 |

所有修复都在各自层级内完成，不需要修改 channel-server 基础设施（engine/ 和 server.py）。

---

## Bug 8: zchat-status.wasm 不存在

**现象**: Zellij 底部显示 "error in plugin"

**根因**: `layout.kdl` 引用 `file:~/.zchat/plugins/zchat-status.wasm`，但该 wasm 文件从未构建。`zchat/cli/data/plugins/` 中只有 `.gitkeep`。`_ensure_plugins()` 尝试从 bundled dir 复制但源文件不存在。

**影响**: 不影响功能，只是 Zellij 状态栏异常。

**修复**: 需要构建 zchat-status wasm plugin，或从 layout 中移除该 plugin 引用。

**修复位置**: `zchat/cli/layout.py` 和 `zchat/cli/app.py` 中的 layout 生成逻辑
