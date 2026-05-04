from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flaura.core.app import FlauraApp

CommandHandler = Callable[["FlauraApp", list[str]], str | None]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandHandler] = {}

    def register(self, name: str, handler: CommandHandler) -> None:
        self._commands[name] = handler

    def names(self) -> list[str]:
        return list(self._commands.keys())

    def execute(self, app: FlauraApp, line: str) -> str | None:
        parts = line.strip().split()
        if not parts:
            return None
        name, args = parts[0], parts[1:]
        handler = self._commands.get(name)
        if not handler:
            return f"unknown command: {name}"
        try:
            return handler(app, args)
        except Exception as e:
            return f"error: {e}"


def cmd_quit(app: FlauraApp, args: list[str]) -> str | None:
    app.quit()
    return None


def cmd_set(app: FlauraApp, args: list[str]) -> str | None:
    if not args:
        return "usage: :set vi | :set novi"
    flag = args[0]
    if flag == "vi":
        app.set_vi_mode(True)
    elif flag == "novi":
        app.set_vi_mode(False)
    else:
        return f"unknown flag: {flag}"
    return None


def cmd_plugin(app: FlauraApp, args: list[str]) -> str | None:
    if not args:
        return f"usage: :plugin <name>; available: {app.list_plugins()}"
    try:
        app.switch_plugin(args[0])
    except KeyError as e:
        return str(e)
    return None


def cmd_window(app: FlauraApp, args: list[str]) -> str | None:
    return "windows not yet implemented (Phase 15)"


def make_default_registry() -> CommandRegistry:
    reg = CommandRegistry()
    reg.register("quit", cmd_quit)
    reg.register("set", cmd_set)
    reg.register("plugin", cmd_plugin)
    reg.register("window", cmd_window)
    return reg
