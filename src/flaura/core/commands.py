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



def cmd_plugins(app: FlauraApp, args: list[str]) -> str | None:
    plugins = app.list_plugins()
    if not plugins:
        return "no plugins loaded"
    lines = [f"  {p.name:<16} {p.description}" for p in plugins]
    return "loaded plugins:\n" + "\n".join(lines)


def cmd_tools(app: FlauraApp, args: list[str]) -> str | None:
    tools = app.list_tools()
    if not tools:
        return "no tools available"
    lines = [f"  {t.name:<20} ({t.plugin_name})  — {t.description}" for t in tools]
    return "available tools:\n" + "\n".join(lines)


def cmd_plugin(app: FlauraApp, args: list[str]) -> str | None:
    if not args:
        return "usage: :plugin install <git-url> | :plugin remove <name> | :plugin create <name>"
    sub = args[0]
    if sub == "install":
        if len(args) < 2:
            return "usage: :plugin install <git-url>"
        return f"install not yet wired — would clone {args[1]} to ~/.flaura/plugins/"
    if sub == "remove":
        if len(args) < 2:
            return "usage: :plugin remove <name>"
        try:
            app.unregister_plugin(args[1])
            return f"removed plugin: {args[1]}"
        except Exception as e:
            return f"error: {e}"
    if sub == "create":
        if len(args) < 2:
            return "usage: :plugin create <name>"
        try:
            path = app.create_plugin(args[1])
            return f"created plugin scaffold at {path} — restart flaura to load it"
        except ValueError as e:
            return f"error: {e}"
    return f"unknown subcommand: {sub}"


_PROVIDERS = ("ollama", "echo")


def cmd_provider(app: FlauraApp, args: list[str]) -> str | None:
    if not args:
        return f"provider: {app.provider_name()}"
    name = args[0]
    model = args[1] if len(args) > 1 else None
    try:
        active = app.set_provider(name, model=model)
        return f"switched to {active}"
    except Exception as e:
        return f"error: {e}"


def make_default_registry() -> CommandRegistry:
    reg = CommandRegistry()
    reg.register("quit", cmd_quit)
    reg.register("plugins", cmd_plugins)
    reg.register("tools", cmd_tools)
    reg.register("plugin", cmd_plugin)
    reg.register("provider", cmd_provider)
    return reg
