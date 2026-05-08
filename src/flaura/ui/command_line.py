from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

if TYPE_CHECKING:
    from flaura.core.app import FlauraApp
    from flaura.core.commands import CommandRegistry


class CommandCompleter(Completer):
    """Live completions for `:command [args...]` syntax."""

    def __init__(self, app: FlauraApp, commands: CommandRegistry) -> None:
        self._app = app
        self._commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.split(" ")

        # First token: command name
        if len(parts) == 1:
            prefix = parts[0]
            for name in self._commands.names():
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
            return

        cmd = parts[0]
        rest = parts[-1]  # last token = what we're currently completing

        if cmd == "set" and len(parts) == 2:
            for opt in ("vi", "novi"):
                if opt.startswith(rest):
                    yield Completion(opt, start_position=-len(rest))

        elif cmd == "plugin" and len(parts) == 2:
            for sub in ("install", "remove"):
                if sub.startswith(rest):
                    yield Completion(sub, start_position=-len(rest))

        elif cmd == "plugin" and len(parts) == 3 and parts[1] == "remove":
            for p in self._app.list_plugins():
                if p.name.startswith(rest):
                    yield Completion(p.name, start_position=-len(rest))
