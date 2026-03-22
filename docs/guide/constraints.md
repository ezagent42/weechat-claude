# 已知限制与路线图

## 已知限制

| 限制 | 影响 | 应对方案 |
|------|------|----------|
| Channel MCP 是 research preview | 必须使用 `--dangerously-load-development-channels` flag | 等待正式发布 |
| Claude Code 需要登录 | 不支持 API key 认证 | 使用 claude.ai 账号 |
| `--dangerously-skip-permissions` | Claude 无需确认即可执行文件操作 | 仅在信任环境使用 |
| Zenoh Python + WeeChat .so | 部分系统上可能存在动态库冲突 | 计划中：Zenoh sidecar 进程 |
| 无跨 session 历史 | 重启后消息丢失 | WeeChat logger 自动保存本地；未来接入 zenohd storage |

## 路线图

- **Agent 间通信** — Agent 通过 private topic 直接协作
- **zenohd + storage backend** — 接入持久化后端，提供跨 session 消息历史
- **飞书桥接** — 飞书作为另一个 Zenoh 节点，复用消息总线
- **Ed25519 签名** — 消息签名验证，防止冒充
- **Web UI** — 通过 WeeChat relay API 暴露 Web 前端
