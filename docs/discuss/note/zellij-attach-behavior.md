# Zellij Attach 行为说明

## 现象

`uv run zchat project use <name>` 在终端 A 执行后：
- 终端 A 被 `os.execvp("zellij", ["zellij", "attach", ...])` 替换
- 如果终端 A 不支持 TUI 渲染（如 Claude Code Bash tool），会卡住
- 需要在**另一个终端 B** 执行 `zellij attach zchat-<project>` 才能看到 Zellij UI

## 自动化测试影响

conftest.py 中不能直接调用 `zchat project use`（会卡住）。正确做法：

```bash
# 步骤 1: 设置 default project（不 attach）
uv run zchat project use <name> --no-attach

# 步骤 2: 创建 Zellij session（后台）
# zchat project use 不带 --no-attach 时内部调用 _launch_project_session
# 但 subprocess 中无法 attach，所以需要单独处理 session 创建
zellij attach --create-background zchat-<project>

# 或者直接用完整流程（在交互终端中）
uv run zchat project use <name>
# 然后在另一个终端 zellij attach
```

## 手动测试流程

```bash
# 终端 A
uv run zchat project use prerelease-test
# 终端 A 变成 zellij attach（可能看不到 UI）

# 终端 B
zellij attach zchat-prerelease-test
# 在这里操作 zchat
```
