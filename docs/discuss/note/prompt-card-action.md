# Task: 飞书卡片回调 (card.action.trigger) + CSAT 评分闭环

> 复制以下 prompt 到新 session 中执行。
> 单个 Task，走 dev-loop 六步闭环。

---

## Prompt

```
你被启动在 zchat 项目根目录 (`~/projects/zchat/`)。
代码在 `zchat-channel-server/` submodule 内，`feat/architecture-split` 分支。

## 目标

实现飞书卡片回调（card.action.trigger）支持，让 CSAT 评分卡片点击完成闭环。
这是 Phase Final (pre-release) 的前置依赖。

完整 pre-release 计划在 `docs/discuss/plan/07-phase-final-testing.md`。
架构决策在 `docs/discuss/note/prerelease-todo.md`。
Spec 在 `docs/discuss/spec/channel-server/09-feishu-bridge.md`。

## 当前状态

- Phase 4.6 全部 7 个 Task 已完成: 197 tests, 195 passed, 2 errors (WebSocket flaky)
- 飞书平台已配置: card.action.trigger 事件已订阅，长连接 (WSS) 模式
- .artifacts/ 下已有 36 个 artifact (9 个 Task 证据链完整)
- CSAT 评分卡片已实现: `feishu_bridge/visibility_router.py:276-295`
- channel-server CSAT 接收端已实现: `server.py:408-416`

## 问题

`lark_oapi` 1.5.3（当前最新版）的 WSS client 收到 `MessageType.CARD` 帧后直接 return，不分发：

```python
# .venv/.../lark_oapi/ws/client.py:264
elif message_type == MessageType.CARD:
    return  # ← 卡片回调被静默丢弃
```

SDK 没有 card_handler 注册机制。需要继承 Client 补上 CARD 分发。

## 工作环境

```bash
cd zchat-channel-server
git checkout feat/architecture-split

# 验证基线
uv run pytest tests/ -v --tb=short
# Expected: 195+ passed, 0 failed
```

## Dev-loop 六步闭环

Artifact ID 前缀: `cs-*-card-action`

### Step 1: eval-doc

/dev-loop-skills:skill-5-feature-eval simulate
# 主题: "飞书卡片回调 — CardAwareClient + CSAT 评分闭环"
# 产出: .artifacts/eval-docs/cs-eval-card-action.md

eval-doc 必须覆盖的行为预期:
1. lark_oapi WSS client 收到 MessageType.CARD 帧 → 分发到注册的 card_handler
2. card_handler 解析 payload.action.value 提取 score + conv_id
3. bridge 通过 Bridge API WebSocket 发送 {"type": "customer_message", "conversation_id": conv_id, "csat_score": N}
4. channel-server _on_customer_message 调用 set_csat() 完成闭环
5. 非 CARD 帧（EVENT 等）仍走原 SDK 逻辑，不受影响
6. card_handler 异常不 crash WSS 连接
7. payload 缺少 score/conv_id 时静默忽略

### Step 2: test-plan

/dev-loop-skills:skill-2-test-plan-generator
# 输入: eval-doc + 下方 test-plan 表
# 产出: .artifacts/test-plans/cs-plan-card-action.md

| # | 测试名 | 类型 | 验证点 |
|---|--------|------|--------|
| 1 | test_card_aware_client_dispatches_card | unit | CARD 帧 → card_handler 被调用，payload 正确 |
| 2 | test_event_frame_delegates_to_super | unit | EVENT 帧 → 走原 SDK 逻辑，card_handler 不被调用 |
| 3 | test_card_handler_exception_swallowed | unit | handler 抛异常 → 连接不断，返回 500 Response |
| 4 | test_card_action_extracts_score | unit | payload {"action":{"value":{"score":"4","conv_id":"c1"}}} → 解析出 score=4, conv_id="c1" |
| 5 | test_card_action_sends_csat_to_bridge | unit | 解析后通过 Bridge API 发送 customer_message + csat_score |
| 6 | test_card_action_missing_fields_noop | unit | 缺 score 或 conv_id → 不发送，不报错 |
| 7 | test_csat_e2e_card_to_score | E2E | 模拟 card action → Bridge API 收到 → conversation.resolution.csat_score 被设置 |
| 8 | test_csat_e2e_invalid_score_ignored | E2E | 无效 score → conversation 不受影响 |

### Step 3: test-code

/dev-loop-skills:skill-3-test-code-writer
# 产出:
#   feishu_bridge/tests/test_card_action.py (6 个 unit)
#   tests/e2e/test_csat_flow.py (2 个 E2E)

### Step 4: TDD 实现

新建 feishu_bridge/ws_client.py (~60行):
- class CardAwareClient(lark.ws.Client)
- __init__ 增加 card_handler 参数
- 覆写 _handle_data_frame: CARD 帧 → 解析 payload → card_handler(payload) → 构造 Response 写回
- 其他帧 → super()._handle_data_frame(frame)

关键 SDK 内部引用:
- from lark_oapi.ws.const import HEADER_TYPE, HEADER_BIZ_RT, HEADER_MESSAGE_ID, HEADER_TRACE_ID, HEADER_SUM, HEADER_SEQ
- from lark_oapi.ws.enum import FrameType, MessageType
- from lark_oapi.ws.model import Response
- from lark_oapi.ws.pb.pbbp2_pb2 import Frame
- from lark_oapi.core.json import JSON
- 原始 _handle_data_frame 在 .venv/.../lark_oapi/ws/client.py:240-281，必须读它理解完整的帧处理流程再写覆写

修改 feishu_bridge/bridge.py:
- 新增 _on_card_action(self, payload) → 解析 action.value → 发 csat 到 Bridge API
- start() 中 lark.ws.Client 替换为 CardAwareClient，传入 card_handler=self._on_card_action

注册: /dev-loop-skills:skill-6-artifact-registry register --type code-diff --id cs-diff-card-action

## 约束

- engine/ protocol/ bridge_api/ transport/ 全部 0 改动
- 新增文件: feishu_bridge/ws_client.py + 测试文件
- 修改文件: feishu_bridge/bridge.py (start 方法 + _on_card_action)
- 回归: 全部已有测试必须继续 PASS

### Step 5: test-run

/dev-loop-skills:skill-4-test-runner
# 新增: uv run pytest feishu_bridge/tests/test_card_action.py tests/e2e/test_csat_flow.py -v
# 回归: uv run pytest tests/unit/ tests/e2e/ feishu_bridge/tests/ -v

### Step 6: artifact registry

/dev-loop-skills:skill-6-artifact-registry register --type e2e-report --id cs-report-card-action

## 闭环完成标志

1. .artifacts/ 下新增 4 个 artifact:
   - cs-eval-card-action (eval-doc, status: confirmed)
   - cs-plan-card-action (test-plan, status: executed)
   - cs-diff-card-action (code-diff, status: confirmed)
   - cs-report-card-action (e2e-report, status: confirmed)
2. registry.json 更新（从 36 → 40 artifacts）
3. 新增测试全部 PASS，回归 0 FAIL

## 提交

```bash
git add feishu_bridge/ws_client.py feishu_bridge/bridge.py \
        feishu_bridge/tests/test_card_action.py tests/e2e/test_csat_flow.py \
        .artifacts/
git commit -m "feat: CardAwareClient — 飞书卡片回调(card.action.trigger) + CSAT 评分闭环"
```
```
