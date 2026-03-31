"""Agent lifecycle management: create workspace, spawn tmux, track state."""

import json
import os
import shlex
import shutil
import tempfile
import time

import libtmux

from zchat.cli.tmux import get_or_create_session, pane_alive
from zchat.cli.template_loader import load_template, render_env, get_start_script, _parse_env_file
from zchat_protocol.naming import scoped_name, AGENT_SEPARATOR


DEFAULT_STATE_FILE = os.path.expanduser("~/.local/state/zchat/agents.json")


class AgentManager:
    def __init__(self, irc_server: str, irc_port: int, irc_tls: bool,
                 irc_password: str,
                 username: str, default_channels: list[str],
                 env_file: str = "",
                 default_type: str = "claude",
                 tmux_session: str = "zchat",
                 state_file: str = DEFAULT_STATE_FILE,
                 project_dir: str = ""):
        self.irc_server = irc_server
        self.irc_port = irc_port
        self.irc_tls = irc_tls
        self.irc_password = irc_password
        self.username = username
        self.default_channels = default_channels
        self.env_file = env_file
        self.default_type = default_type
        self._tmux_session_name = tmux_session
        self._tmux_session: libtmux.Session | None = None
        self._state_file = state_file
        self.project_dir = project_dir
        self._agents: dict[str, dict] = {}
        self._load_state()

    @property
    def tmux_session(self) -> libtmux.Session:
        if self._tmux_session is None:
            self._tmux_session = get_or_create_session(self._tmux_session_name)
        return self._tmux_session

    def scoped(self, name: str) -> str:
        return scoped_name(name, self.username)

    def create(self, name: str, workspace: str | None = None,
               channels: list[str] | None = None,
               agent_type: str | None = None) -> dict:
        """Create and launch a new agent. Returns agent info dict."""
        name = self.scoped(name)
        if name in self._agents and self._agents[name].get("status") == "running":
            raise ValueError(f"{name} already exists and is running")

        agent_type = agent_type or self.default_type
        channels = channels or list(self.default_channels)
        agent_workspace = workspace or self._create_workspace(name)

        window_name = self._spawn_tmux(name, agent_workspace, agent_type, channels)

        self._agents[name] = {
            "type": agent_type,
            "workspace": agent_workspace,
            "window_name": window_name,
            "status": "starting",
            "created_at": time.time(),
            "channels": channels,
        }
        self._save_state()
        return self._agents[name]

    def stop(self, name: str, force: bool = False):
        """Stop an agent."""
        name = self.scoped(name)
        agent = self._agents.get(name)
        if not agent:
            raise ValueError(f"Unknown agent: {name}")
        if agent["status"] == "offline":
            raise ValueError(f"{name} is already offline")
        self._force_stop(name)
        agent["status"] = "offline"
        self._cleanup_workspace(name)
        self._save_state()

    def restart(self, name: str):
        """Stop then re-create with same config."""
        name = self.scoped(name)
        agent = self._agents.get(name)
        if not agent:
            raise ValueError(f"Unknown agent: {name}")
        channels = list(agent.get("channels", self.default_channels))
        agent_type = agent.get("type", self.default_type)
        self.stop(name)
        base_name = name.split(AGENT_SEPARATOR, 1)[-1] if AGENT_SEPARATOR in name else name
        self.create(base_name, channels=channels, agent_type=agent_type)

    def list_agents(self) -> dict[str, dict]:
        """Return all agents with refreshed status."""
        for name, info in self._agents.items():
            if info.get("status") != "offline":
                info["status"] = self._check_alive(name)
        self._save_state()
        return dict(self._agents)

    def get_status(self, name: str) -> dict:
        name = self.scoped(name)
        agent = self._agents.get(name)
        if not agent:
            raise ValueError(f"Unknown agent: {name}")
        if agent["status"] != "offline":
            agent["status"] = self._check_alive(name)
        return agent

    def _create_workspace(self, name: str) -> str:
        if self.project_dir:
            workspace = os.path.join(self.project_dir, "agents", name)
        else:
            safe = name.replace(AGENT_SEPARATOR, "_")
            workspace = os.path.join(tempfile.gettempdir(), f"zchat-{safe}")
        os.makedirs(workspace, exist_ok=True)
        return workspace

    def _build_env_context(self, name: str, workspace: str, channels: list[str]) -> dict:
        """Build the context dict for template placeholder rendering."""
        channels_str = ",".join(ch.lstrip("#") for ch in channels)
        context = {
            "agent_name": name,
            "irc_server": self.irc_server,
            "irc_port": str(self.irc_port),
            "irc_channels": channels_str,
            "irc_tls": str(self.irc_tls).lower(),
            "irc_password": self.irc_password,
            "workspace": workspace,
            "zchat_project_dir": self.project_dir,
            "irc_sasl_user": "",
            "irc_sasl_pass": "",
            "auth_token_file": "",
        }
        if self.project_dir:
            from zchat.cli.auth import get_credentials, _global_auth_dir
            creds = get_credentials()
            if creds:
                _, sasl_pass = creds
                context["irc_sasl_user"] = name
                context["irc_sasl_pass"] = sasl_pass
                context["auth_token_file"] = os.path.join(_global_auth_dir(), "auth.json")
        return context

    def _spawn_tmux(self, name: str, workspace: str, agent_type: str,
                    channels: list[str]) -> str:
        context = self._build_env_context(name, workspace, channels)
        env = render_env(agent_type, context)

        # Overlay project-level env_file (lower priority than template env)
        if self.env_file and os.path.isfile(self.env_file):
            project_env = _parse_env_file(self.env_file)
            merged = dict(project_env)
            merged.update(env)
            env = merged

        start_script = get_start_script(agent_type)

        # Write env to workspace
        env_file_path = os.path.join(workspace, ".zchat-env")
        with open(env_file_path, "w") as f:
            for k, v in env.items():
                f.write(f"export {k}={shlex.quote(v)}\n")

        cmd = f"cd '{workspace}' && source .zchat-env && bash '{start_script}'"

        # Create dedicated window (not pane) for this agent
        window = self.tmux_session.new_window(
            window_name=name, window_shell=cmd, attach=False,
        )
        return window.window_name

    def _force_stop(self, name: str):
        from zchat.cli.tmux import find_window, window_alive
        agent = self._agents.get(name)
        if not agent:
            return
        wname = agent.get("window_name")
        if not wname:
            return
        window = find_window(self.tmux_session, wname)
        if not window:
            return

        agent_type = agent.get("type", self.default_type)
        try:
            tpl = load_template(agent_type)
            pre_stop = tpl.get("hooks", {}).get("pre_stop", "")
        except Exception:
            pre_stop = ""

        if pre_stop:
            pane = window.active_pane
            if pane:
                pane.send_keys(pre_stop, enter=True)
            # Poll for up to 10 seconds
            for _ in range(20):
                time.sleep(0.5)
                if not window_alive(self.tmux_session, wname):
                    return
        # Kill window as fallback
        try:
            window.kill()
        except Exception:
            pass

    def _cleanup_workspace(self, name: str):
        """Delete ready marker on stop. Preserve workspace for restart."""
        if self.project_dir:
            ready_file = os.path.join(self.project_dir, "agents", f"{name}.ready")
            if os.path.isfile(ready_file):
                os.remove(ready_file)
        else:
            # Legacy: clean up /tmp workspaces
            agent = self._agents.get(name)
            if agent:
                ws = agent.get("workspace", "")
                if ws.startswith(tempfile.gettempdir()):
                    shutil.rmtree(ws, ignore_errors=True)

    def _check_alive(self, name: str) -> str:
        from zchat.cli.tmux import window_alive
        agent = self._agents.get(name)
        if not agent:
            return "offline"
        # Support both new (window_name) and legacy (pane_id) state
        wname = agent.get("window_name")
        if wname:
            return "running" if window_alive(self.tmux_session, wname) else "offline"
        pid = agent.get("pane_id")
        if pid:
            return "running" if pane_alive(self.tmux_session, pid) else "offline"
        return "offline"

    def send(self, name: str, text: str):
        """Send text to agent's tmux window."""
        from zchat.cli.tmux import find_window
        name = self.scoped(name)
        agent = self._agents.get(name)
        if not agent:
            raise ValueError(f"Unknown agent: {name}")
        if self._check_alive(name) != "running":
            raise ValueError(f"{name} is not running")
        window = find_window(self.tmux_session, agent["window_name"])
        if window and window.active_pane:
            window.active_pane.send_keys(text, enter=True)

    def _load_state(self):
        if os.path.isfile(self._state_file):
            try:
                with open(self._state_file) as f:
                    data = json.load(f)
                self._agents = data.get("agents", {})
            except (json.JSONDecodeError, OSError):
                self._agents = {}

    def _save_state(self):
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        existing = {}
        if os.path.isfile(self._state_file):
            try:
                with open(self._state_file) as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        existing["agents"] = self._agents
        with open(self._state_file, "w") as f:
            json.dump(existing, f, indent=2)
