"""Command registry for WeeChat plugins.
# TODO: export.py — OpenAPI / JSON Schema / plain text export
"""

from __future__ import annotations
from .types import CommandParam, CommandSpec, CommandResult, ParsedArgs


class CommandRegistry:
    """Decorator-based command registry with dispatch and help generation."""

    def __init__(self, prefix: str):
        self.prefix = prefix
        self.commands: dict[str, CommandSpec] = {}

    def command(self, name: str, args: str, description: str, params: list[CommandParam] | None = None):
        """Decorator to register a command handler."""
        params = params or []

        def decorator(fn):
            spec = CommandSpec(
                name=name, args=args, description=description,
                params=params, handler=fn,
            )
            self.commands[name] = spec
            return fn
        return decorator

    def dispatch(self, buffer, raw_args: str) -> CommandResult:
        """Parse raw_args and dispatch to the matching command handler."""
        tokens = raw_args.split() if raw_args.strip() else []

        if not tokens or tokens[0] == "help":
            return self._generate_help()

        subcmd = tokens[0]
        if subcmd not in self.commands:
            return CommandResult.error(
                f"Unknown command: /{self.prefix} {subcmd}. "
                f"Use /{self.prefix} help for available commands."
            )

        spec = self.commands[subcmd]
        remainder = tokens[1:]
        parsed = self._parse_args(spec, remainder, raw_args)

        if isinstance(parsed, CommandResult):
            return parsed  # Validation error

        return spec.handler(buffer, parsed)

    def _parse_args(self, spec: CommandSpec, tokens: list[str], raw: str) -> ParsedArgs | CommandResult:
        """Parse tokens into positional args and flags."""
        positional_params = [p for p in spec.params if not p.name.startswith("--")]
        flag_params = {p.name: p for p in spec.params if p.name.startswith("--")}

        positional: dict[str, str] = {}
        flags: dict[str, str | bool] = {}
        positional_values: list[str] = []

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--"):
                if token in flag_params:
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                        flags[token] = tokens[i + 1]
                        i += 2
                    else:
                        flags[token] = True
                        i += 1
                else:
                    flags[token] = True
                    i += 1
            else:
                positional_values.append(token)
                i += 1

        # Match positional values to params
        for idx, param in enumerate(positional_params):
            if idx < len(positional_values):
                positional[param.name] = positional_values[idx]
            elif param.required:
                return CommandResult.error(
                    f"Missing required argument: {param.name}\n"
                    f"Usage: /{self.prefix} {spec.name} {spec.args}"
                )

        # Check required flags
        for fname, fparam in flag_params.items():
            if fparam.required and fname not in flags:
                return CommandResult.error(f"Missing required flag: {fname}")

        return ParsedArgs(positional=positional, flags=flags, raw=raw)

    def _generate_help(self) -> CommandResult:
        """Generate help text from registered commands."""
        lines = ["Commands:"]
        for name, spec in self.commands.items():
            args_str = f" {spec.args}" if spec.args else ""
            lines.append(f"  /{self.prefix} {name}{args_str} — {spec.description}")
        return CommandResult.ok("\n".join(lines))

    def weechat_help_args(self) -> str:
        """Generate WeeChat hook_command args_description string."""
        return " || ".join(
            f"{spec.name} {spec.args}".strip() for spec in self.commands.values()
        )

    def weechat_completion(self) -> str:
        """Generate WeeChat hook_command completion string."""
        return " || ".join(self.commands.keys())
