#!/usr/bin/env python3
# weechat-agent.py

"""
Claude Code Agent 生命周期管理
依赖 weechat-zenoh.py（通过 WeeChat 命令交互）
"""

import weechat
import json
import os
import subprocess
import tempfile
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from wc_protocol.naming import scoped_name as protocol_scoped_name
from wc_protocol.signals import SIGNAL_MESSAGE_RECEIVED, SIGNAL_PRESENCE_CHANGED
from wc_protocol.sys_messages import make_sys_message, is_sys_message
from wc_protocol.topics import private_topic, make_private_pair
from wc_registry import CommandRegistry
from wc_registry.types import CommandParam, CommandResult, ParsedArgs

SCRIPT_NAME = "weechat-agent"
SCRIPT_AUTHOR = "Allen <ezagent42>"
SCRIPT_VERSION = "0.2.0"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Claude Code agent lifecycle management for WeeChat"

# --- 全局状态 ---
agents = {}                # name → { workspace, pane_id, status }
CHANNEL_PLUGIN_DIR = ""    # weechat-channel-server plugin 路径
TMUX_SESSION = ""          # tmux session 名称
USERNAME = ""              # 当前用户名（用于 agent 名称作用域）
PRIMARY_AGENT = ""         # 主 agent 全名（如 alice:agent0）


def scoped_name(name):
    """给 agent 名称加上用户名前缀（如已有前缀则不重复添加）。"""
    return protocol_scoped_name(name, USERNAME)


pending_stops = {}   # msg_id → {name, buffer, timer}
pending_joins = {}   # msg_id → {agent_name, channel, buffer, timer}
pending_status = {}  # msg_id → {name, buffer, timer}


def _send_sys_message(target_agent: str, msg: dict):
    """Send a sys message to an agent via the zenoh_raw_publish signal."""
    pair = make_private_pair(USERNAME, target_agent)
    topic = private_topic(pair)
    weechat.hook_signal_send("zenoh_raw_publish",
        weechat.WEECHAT_HOOK_SIGNAL_STRING,
        json.dumps({"topic": topic, "payload": msg}))


def _force_stop_agent(name):
    """Force stop via tmux send-keys."""
    agent = agents.get(name)
    if agent and agent.get("pane_id"):
        subprocess.run(["tmux", "send-keys", "-t", agent["pane_id"], "/exit", "Enter"],
                       capture_output=True)


# ============================================================
# 初始化
# ============================================================

def _suggest_channel_plugin_dir():
    """Try to find weechat-channel-server relative to this plugin."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weechat-channel-server"),
        os.path.expanduser("~/Workspace/weechat-claude/weechat-channel-server"),
    ]
    for path in candidates:
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "server.py")):
            return os.path.realpath(path)
    return None


def agent_init():
    global CHANNEL_PLUGIN_DIR, TMUX_SESSION, USERNAME, PRIMARY_AGENT

    CHANNEL_PLUGIN_DIR = weechat.config_get_plugin("channel_plugin_dir")
    TMUX_SESSION = weechat.config_get_plugin("tmux_session") or "weechat-claude"
    USERNAME = weechat.config_string(
        weechat.config_get("plugins.var.python.weechat-zenoh.nick")
    ) or os.environ.get("USER", "user")

    PRIMARY_AGENT = scoped_name("agent0")

    # 注册 agent0（由 start.sh 预启动）
    if weechat.config_get_plugin("agent0_workspace"):
        agent0_pane = _find_claude_pane()
        agents[PRIMARY_AGENT] = {
            "workspace": weechat.config_get_plugin("agent0_workspace"),
            "status": "running",
            "pane_id": agent0_pane,
        }
        weechat.command("", f"/zenoh join @{PRIMARY_AGENT}")

    # 监听消息 signal，检测 Agent 的结构化命令输出
    weechat.hook_signal(SIGNAL_MESSAGE_RECEIVED,
                        "on_message_signal_cb", "")

    # 监听 presence signal，更新 Agent 状态
    weechat.hook_signal(SIGNAL_PRESENCE_CHANGED,
                        "on_presence_signal_cb", "")

    # 监听 sys message signal
    weechat.hook_signal("zenoh_sys_message", "on_sys_message_cb", "")


# ============================================================
# Agent Workspace 管理
# ============================================================

def _create_agent_workspace(name):
    """Create a temporary workspace with .mcp.json for the agent."""
    safe = name.replace(":", "-")
    workspace = os.path.join(tempfile.gettempdir(), f"wc-agent-{safe}")
    os.makedirs(workspace, exist_ok=True)

    config = {
        "mcpServers": {
            "weechat-channel": {
                "type": "stdio",
                "command": "uv",
                "args": [
                    "run", "--project", CHANNEL_PLUGIN_DIR,
                    "python3", os.path.join(CHANNEL_PLUGIN_DIR, "server.py"),
                ],
                "env": {
                    "AGENT_NAME": name,
                    "AUTOJOIN_CHANNELS": "general",
                },
            }
        }
    }
    with open(os.path.join(workspace, ".mcp.json"), "w") as f:
        json.dump(config, f)
    return workspace


def _cleanup_agent_workspace(name):
    """Remove the agent's temporary workspace directory."""
    import shutil
    safe = name.replace(":", "-")
    workspace = os.path.join(tempfile.gettempdir(), f"wc-agent-{safe}")
    shutil.rmtree(workspace, ignore_errors=True)


def _find_claude_pane():
    """Find the tmux pane running claude in the current session."""
    try:
        result = subprocess.run(
            ["tmux", "list-panes", "-t", TMUX_SESSION,
             "-F", "#{pane_id}:#{pane_current_command}"],
            capture_output=True, text=True)
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                pane_id, cmd = line.split(":", 1)
                if cmd and cmd not in ("weechat", "zsh", "bash"):
                    return pane_id
    except Exception:
        pass
    return ""


def _last_agent_pane():
    """Return the pane_id of the last registered agent (for split targeting)."""
    for name in reversed(list(agents.keys())):
        pane = agents[name].get("pane_id")
        if pane:
            return pane
    return ""


# ============================================================
# Agent 创建
# ============================================================

def create_agent(name, workspace):
    """Create and register an agent. Caller must pass already-scoped name and handle output."""
    if not CHANNEL_PLUGIN_DIR:
        return

    # Create isolated workspace with .mcp.json for this agent
    agent_workspace = _create_agent_workspace(name)
    cmd = (
        f"cd '{agent_workspace}' && "
        f"AGENT_NAME='{name}' "
        f"claude "
        f"--permission-mode bypassPermissions "
        f"--dangerously-load-development-channels server:weechat-channel"
    )
    # Split vertically from the last agent pane (right column)
    target = _last_agent_pane() or TMUX_SESSION
    result = subprocess.run(
        ["tmux", "split-window", "-v", "-P", "-F", "#{pane_id}",
         "-t", target, cmd],
        capture_output=True, text=True
    )
    pane_id = result.stdout.strip()

    agents[name] = {
        "workspace": agent_workspace,
        "status": "starting",
        "pane_id": pane_id,
        "created_at": time.time(),
    }

    # Auto-confirm the --dangerously-load-development-channels prompt
    weechat.hook_timer(3000, 0, 1, "_auto_confirm_cb", pane_id)

    # 创建 private buffer
    weechat.command("", f"/zenoh join @{name}")


def _auto_confirm_cb(data, remaining_calls):
    """Auto-confirm the development channels warning prompt."""
    pane_id = data
    subprocess.run(
        ["tmux", "send-keys", "-t", pane_id, "Enter"],
        capture_output=True
    )
    return weechat.WEECHAT_RC_OK


# ============================================================
# Signal 处理
# ============================================================

def on_message_signal_cb(data, signal, signal_data):
    """监听 zenoh 消息，检测 Agent 的结构化命令"""
    try:
        msg = json.loads(signal_data)
        nick = msg.get("nick", "")
        body = msg.get("body", "")

        # 检测 Agent 输出的结构化命令
        if nick in agents and body.strip().startswith("{"):
            try:
                cmd = json.loads(body.strip())
                if cmd.get("action") == "create_agent":
                    scoped = scoped_name(cmd["name"])
                    if scoped not in agents and CHANNEL_PLUGIN_DIR:
                        create_agent(
                            scoped,
                            cmd.get("workspace", os.getcwd())
                        )
            except (json.JSONDecodeError, KeyError):
                weechat.prnt("", f"[agent] Warning: received malformed structured message from {nick}")

    except Exception:
        pass
    return weechat.WEECHAT_RC_OK


def on_presence_signal_cb(data, signal, signal_data):
    """监听 presence 变化，更新 Agent 状态并通知用户"""
    try:
        ev = json.loads(signal_data)
        nick = ev.get("nick", "")
        online = ev.get("online", False)
        if nick in agents:
            if online:
                if agents[nick]["status"] == "starting":
                    elapsed = time.time() - agents[nick].get("created_at", time.time())
                    weechat.prnt("", f"[agent] {nick} is now ready (took {elapsed:.1f}s)")
                agents[nick]["status"] = "running"
            else:
                if agents[nick].get("pending_restart"):
                    workspace = agents[nick].pop("restart_workspace", agents[nick]["workspace"])
                    agents[nick].pop("pending_restart", None)
                    weechat.prnt("", f"[agent] Restarting {nick}...")
                    weechat.hook_timer(1000, 0, 1, "restart_timer_cb",
                                       json.dumps({"name": nick, "workspace": workspace}))
                else:
                    agents[nick]["status"] = "offline"
                    # Clean up workspace when agent goes offline
                    _cleanup_agent_workspace(nick)
                    weechat.prnt("",
                        f"[agent] {nick} is now offline")
    except Exception:
        pass
    return weechat.WEECHAT_RC_OK


def on_sys_message_cb(data, signal, signal_data):
    """Handle sys.* messages from agents."""
    try:
        msg = json.loads(signal_data)
    except json.JSONDecodeError:
        return weechat.WEECHAT_RC_OK

    msg_type = msg.get("type", "")
    ref_id = msg.get("ref_id")

    if msg_type == "sys.stop_confirmed" and ref_id in pending_stops:
        info = pending_stops.pop(ref_id)
        weechat.unhook(info["timer"])
        weechat.prnt("", f"[agent] {info['name']} is shutting down...")
        _force_stop_agent(info["name"])

    elif msg_type == "sys.join_confirmed" and ref_id in pending_joins:
        info = pending_joins.pop(ref_id)
        weechat.unhook(info["timer"])
        channel = msg.get("body", {}).get("channel", info["channel"])
        weechat.prnt("", f"[agent] {info['agent_name']} joined {channel}")
        # Track channel membership locally
        agent_name = info["agent_name"]
        if agent_name in agents:
            agents[agent_name].setdefault("channels", [])
            if channel not in agents[agent_name]["channels"]:
                agents[agent_name]["channels"].append(channel)

    elif msg_type == "sys.status_response" and ref_id in pending_status:
        info = pending_status.pop(ref_id)
        weechat.unhook(info["timer"])
        result = _format_agent_status(info["name"], remote=msg.get("body", {}))
        weechat.prnt(info["buffer"], f"[agent] {result.message}")

    elif msg_type == "sys.ack":
        pass  # Delivery confirmed — silent tracking for now

    return weechat.WEECHAT_RC_OK


# ============================================================
# /agent 命令
# ============================================================

agent_registry = CommandRegistry(prefix="agent")


@agent_registry.command(
    name="create",
    args="<name> [--workspace <path>]",
    description="Launch new Claude Code instance",
    params=[
        CommandParam("name", required=True, help="Agent name (without username prefix)"),
        CommandParam("--workspace", required=False, help="Custom workspace path"),
    ],
)
def cmd_agent_create(buffer, args: ParsedArgs) -> CommandResult:
    name = args.get("name")
    workspace = args.get("--workspace", os.getcwd())
    scoped = scoped_name(name)
    if scoped in agents:
        return CommandResult.error(f"{scoped} already exists")
    if not CHANNEL_PLUGIN_DIR:
        suggested = _suggest_channel_plugin_dir()
        if suggested:
            return CommandResult.error(
                f"channel_plugin_dir not set.\n"
                f"  Detected: {suggested}\n"
                f"  Run: /set plugins.var.python.weechat-agent.channel_plugin_dir {suggested}"
            )
        return CommandResult.error(
            "channel_plugin_dir not set.\n"
            "  Run: /set plugins.var.python.weechat-agent.channel_plugin_dir /path/to/weechat-channel-server"
        )
    create_agent(scoped, workspace)
    agent = agents[scoped]
    return CommandResult.ok(
        f"Created {scoped}\n"
        f"  workspace: {agent['workspace']}\n"
        f"  pane: {agent['pane_id']}\n"
        f"  tmux: Ctrl+b then arrow keys to navigate"
    )


@agent_registry.command(
    name="list", args="", description="List agents with status, uptime, channels",
    params=[],
)
def cmd_agent_list(buffer, args: ParsedArgs) -> CommandResult:
    if not agents:
        return CommandResult.ok("No agents")
    lines = ["Agents:"]
    for name, info in agents.items():
        status = info["status"]
        pane = info.get("pane_id", "—")
        ws = info["workspace"]

        # Uptime
        if status != "offline" and "created_at" in info:
            elapsed = time.time() - info["created_at"]
            if elapsed >= 3600:
                uptime = f"{elapsed / 3600:.0f}h"
            elif elapsed >= 60:
                uptime = f"{elapsed / 60:.0f}m"
            else:
                uptime = f"{elapsed:.0f}s"
        else:
            uptime = "—"

        # Channels
        ch_list = info.get("channels", [])
        ch_str = ", ".join(ch_list) if ch_list else "—"

        lines.append(f"  {name}\t{status}\t{uptime}\t{pane}\t{ch_str}\t{ws}")
    return CommandResult.ok("\n".join(lines))


@agent_registry.command(
    name="join",
    args="<agent> <channel>",
    description="Ask agent to join a channel (with confirmation)",
    params=[
        CommandParam("agent", required=True, help="Agent name"),
        CommandParam("channel", required=True, help="Channel name (e.g. #dev)"),
    ],
)
def cmd_agent_join(buffer, args: ParsedArgs) -> CommandResult:
    agent_name = scoped_name(args.get("agent"))
    channel = args.get("channel")
    if agent_name not in agents:
        return CommandResult.error(f"Unknown agent: {agent_name}")

    msg = make_sys_message(USERNAME, "sys.join_request", {"channel": channel})
    _send_sys_message(agent_name, msg)

    timer = weechat.hook_timer(10000, 0, 1, "_join_timeout_cb", msg["id"])
    pending_joins[msg["id"]] = {
        "agent_name": agent_name, "channel": channel,
        "buffer": buffer, "timer": timer,
    }
    return CommandResult.ok(f"Asking {agent_name} to join {channel}...")


def _join_timeout_cb(data, remaining_calls):
    msg_id = data
    if msg_id in pending_joins:
        info = pending_joins.pop(msg_id)
        weechat.prnt("", f"[agent] {info['agent_name']} did not confirm joining {info['channel']} (request may still be pending)")
    return weechat.WEECHAT_RC_OK


def _initiate_agent_stop(name: str):
    """Send sys.stop_request or force-stop. Used by both stop and restart commands."""
    agent = agents[name]
    if agent["status"] == "starting":
        _force_stop_agent(name)
        return
    msg = make_sys_message(USERNAME, "sys.stop_request", {"reason": "stop requested"})
    _send_sys_message(name, msg)
    timer = weechat.hook_timer(5000, 0, 1, "_stop_timeout_cb", name)
    pending_stops[msg["id"]] = {"name": name, "buffer": "", "timer": timer}


@agent_registry.command(
    name="stop",
    args="<name>",
    description="Stop a running agent (not agent0)",
    params=[CommandParam("name", required=True, help="Agent name")],
)
def cmd_agent_stop(buffer, args: ParsedArgs) -> CommandResult:
    name = scoped_name(args.get("name"))
    if name not in agents:
        return CommandResult.error(f"Unknown agent: {name}")
    if name.endswith(":agent0"):
        return CommandResult.error(f"{name} is the primary agent and cannot be stopped")

    agent = agents[name]
    if agent["status"] == "offline":
        return CommandResult.error(f"{name} is already offline")

    if agent["status"] == "starting":
        _force_stop_agent(name)
        return CommandResult.ok(f"{name} was still starting, forcing stop...")

    _initiate_agent_stop(name)
    return CommandResult.ok(f"Stopping {name}...")


@agent_registry.command(
    name="restart",
    args="<name>",
    description="Restart agent (stop then re-create with same config)",
    params=[CommandParam("name", required=True, help="Agent name")],
)
def cmd_agent_restart(buffer, args: ParsedArgs) -> CommandResult:
    name = scoped_name(args.get("name"))
    if name not in agents:
        return CommandResult.error(f"Unknown agent: {name}")
    if name.endswith(":agent0"):
        return CommandResult.error(f"{name} is the primary agent and cannot be restarted")
    agent = agents[name]
    agent["pending_restart"] = True
    agent["restart_workspace"] = agent["workspace"]
    _initiate_agent_stop(name)
    return CommandResult.ok(f"Restarting {name}...")


def _stop_timeout_cb(data, remaining_calls):
    """Called if agent doesn't respond to sys.stop_request within 5s."""
    name = data
    to_remove = [mid for mid, info in pending_stops.items() if info["name"] == name]
    for mid in to_remove:
        del pending_stops[mid]
    weechat.prnt("", f"[agent] {name} did not respond, forcing stop...")
    _force_stop_agent(name)
    return weechat.WEECHAT_RC_OK


def _format_agent_status(name, remote=None):
    agent = agents[name]
    status = agent["status"]
    if status != "offline" and "created_at" in agent:
        elapsed = time.time() - agent["created_at"]
        mins, secs = divmod(int(elapsed), 60)
        uptime = f"{mins}m {secs}s"
    else:
        uptime = "—"

    lines = [f"{name}"]
    if remote is None and status != "offline":
        lines[0] += " (agent not responding — showing local info only)"
    lines.append(f"  status:    {status}")
    lines.append(f"  uptime:    {uptime}")
    lines.append(f"  pane:      {agent.get('pane_id', '—')}")
    lines.append(f"  workspace: {agent['workspace']}")
    if remote:
        ch = ", ".join(f"#{c}" for c in remote.get("channels", []))
        lines.append(f"  channels:  {ch or '—'}")
        lines.append(f"  messages:  sent {remote.get('messages_sent', 0)}, received {remote.get('messages_received', 0)}")
    else:
        ch = ", ".join(agent.get("channels", []))
        lines.append(f"  channels:  {ch or '—'}")
    return CommandResult.ok("\n".join(lines))


def _status_timeout_cb(data, remaining_calls):
    msg_id = data
    if msg_id in pending_status:
        info = pending_status.pop(msg_id)
        result = _format_agent_status(info["name"], remote=None)
        weechat.prnt(info["buffer"], f"[agent] {result.message}")
    return weechat.WEECHAT_RC_OK


@agent_registry.command(
    name="status",
    args="<name>",
    description="Show detailed single-agent info",
    params=[CommandParam("name", required=True, help="Agent name")],
)
def cmd_agent_status(buffer, args: ParsedArgs) -> CommandResult:
    name = scoped_name(args.get("name"))
    if name not in agents:
        return CommandResult.error(f"Unknown agent: {name}")

    agent = agents[name]
    if agent["status"] == "offline":
        return _format_agent_status(name, remote=None)

    msg = make_sys_message(USERNAME, "sys.status_request", {})
    _send_sys_message(name, msg)

    timer = weechat.hook_timer(3000, 0, 1, "_status_timeout_cb", msg["id"])
    pending_status[msg["id"]] = {"name": name, "buffer": buffer, "timer": timer}
    return CommandResult.ok(f"Querying {name}...")


def agent_cmd_cb(data, buffer, args):
    """WeeChat hook callback — delegates to registry."""
    result = agent_registry.dispatch(buffer, args)
    prefix = "[agent]"
    if result.success:
        weechat.prnt(buffer, f"{prefix} {result.message}")
    else:
        weechat.prnt(buffer, f"{prefix} Error: {result.message}")
    return weechat.WEECHAT_RC_OK


def restart_timer_cb(data, remaining_calls):
    info = json.loads(data)
    scoped = scoped_name(info["name"])
    if scoped not in agents and CHANNEL_PLUGIN_DIR:
        create_agent(scoped, info["workspace"])
    return weechat.WEECHAT_RC_OK


def agent_deinit():
    for name in list(agents.keys()):
        _cleanup_agent_workspace(name)
    return weechat.WEECHAT_RC_OK


# ============================================================
# 插件注册
# ============================================================

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                    SCRIPT_LICENSE, SCRIPT_DESC, "agent_deinit", ""):
    for key, val in {
        "channel_plugin_dir": "",
        "tmux_session": "weechat-claude",
        "agent0_workspace": "",
    }.items():
        if not weechat.config_is_set_plugin(key):
            weechat.config_set_plugin(key, val)

    weechat.hook_command("agent",
        "Manage Claude Code agents",
        agent_registry.weechat_help_args(),
        "",
        agent_registry.weechat_completion(),
        "agent_cmd_cb", "")

    agent_init()
