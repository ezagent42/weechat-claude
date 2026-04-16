# Pre-release 手动测试发现

日期: 2026-04-16

## 发现 1: zchat project use 卡住

`uv run zchat project use prerelease-test` 在终端中执行后卡住，不会自动显示 Zellij UI。

- **原因**: `_create_project_zellij_session()` 中 `zellij.ensure_session()` 用 `subprocess.run(capture_output=True)` 执行 `--new-session-with-layout`，该命令会阻塞等待交互式 session 结束
- **Workaround**: 在另一个终端 `zellij attach zchat-prerelease-test`
- **影响**: conftest 自动化中不能直接调用 `zchat project use`（需要 `--no-attach` + 单独创建 session）

## 发现 2: zchat project use 已包含 WeeChat + ergo

`zchat project use` 内部调用 `_create_project_zellij_session()` 已经启动了 ergo 和 WeeChat tab。不需要再单独执行 `zchat irc daemon start` 和 `zchat irc start`。

- 重复执行 `zchat irc start` 会创建第二个 weechat tab（4 个 tab 而非 3 个）

## 发现 3: agent 回复带 __msg: 前缀

agent 的 reply() MCP tool 发送 `__msg:uuid:text` 格式到 IRC。WeeChat 显示原始 IRC 消息，所以用户看到了前缀。

- **设计**: 这是 channel-server 协议的一部分，`parse_agent_message()` 需要前缀来区分 reply/edit/side
- **体验**: WeeChat 中显示不友好。可在 weechat-zchat-plugin 中过滤前缀（UI 层优化，非阻塞）

## 发现 4: Claude Code tool call 显示折叠

agent tab 中 Claude Code 显示 `Called zchat-agent-mcp (ctrl+o to expand)` 而不是完整回复内容。

- **原因**: Claude Code 对 MCP tool call 结果默认折叠显示
- **Ctrl+O 冲突**: 在 Zellij 中 Ctrl+O 被 Zellij session mode 拦截
- **影响**: 不影响功能，但降低了可观察性

## 发现 5: CHANNEL_PKG_DIR 为空 → plugin error

`settings.local.json` 启用了 `"zchat@ezagent42": true`，但 `.claude-plugin/` 目录未复制到 agent workspace。

- **原因**: `_find_channel_pkg_dir()` 在 `uv tool dir` 下找 `zchat-channel-server`，但我们用的是 editable install，路径不在 uv tool dir 中
- **影响**: Claude Code 报 "error in plugin"。agent slash commands 不可用
- **Workaround**: `cp -r ~/projects/zchat/zchat-channel-server/.claude-plugin ~/.zchat/projects/prerelease-test/agents/yaosh-fast-agent/`
- **根本修复**: `_find_channel_pkg_dir()` 需要 fallback 到 editable install 路径
