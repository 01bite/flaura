from __future__ import annotations

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.styles import Style

from flaura.agent.core import AgentCore
from flaura.agent.providers.echo import EchoProvider
from flaura.core.commands import make_default_registry
from flaura.core.dispatcher import Dispatcher
from flaura.plugins.builtin import BUILTIN_PLUGINS
from flaura.plugins.loader import discover_user_plugins
from flaura.plugins.registry import PluginRegistry
from flaura.ui.command_line import CommandCompleter
from flaura.ui.key_bindings import create_global_key_bindings
from flaura.ui.layout import FlauraLayout

_STYLE = Style.from_dict(
    {
        "status-bar":                  "bg:#444444 #ffffff bold",
        "status-bar.vi":               "bg:#444444 #ff8800 bold",
        "status-bar.thinking":         "bg:#444444 #00ddff bold",
        "separator":                   "bg:#333333 #555555",
        "prompt":                      "#00aa00 bold",
        "prompt.dots":                 "#555555",
        "command-prompt":              "#ffaa00 bold",
        "mode.multi":                  "bg:#333333 #666666",
        "mode.single":                 "bg:#50fa7b #000000",
        "completion-menu":                      "bg:#2d2d2d #ffffff",
        "completion-menu.completion":           "bg:#2d2d2d #ffffff",
        "completion-menu.completion.current":   "bg:#00aa00 #000000 bold",
        "completion-menu.meta.completion":      "bg:#222222 #888888",
        "completion-menu.meta.completion.current": "bg:#007700 #ffffff",
        "scrollbar.background":        "bg:#1a1a1a",
        "scrollbar.button":            "bg:#555555",
        "search":                      "bg:#440044 #ffffff",
        "search.current":              "bg:#aa00aa #ffffff bold",
        "search-toolbar":              "bg:#222222 #ffaa00",
    }
)


class FlauraApp:
    def __init__(self) -> None:
        self._agent: AgentCore | None = None
        self._dispatcher: Dispatcher | None = None

        self._registry = PluginRegistry()
        self._commands = make_default_registry()

        # Load built-in plugins (always available)
        for plugin_class in BUILTIN_PLUGINS:
            self._registry.register(plugin_class())

        # Load user-installed plugins from ~/.flaura/plugins/
        for plugin in discover_user_plugins():
            try:
                self._registry.register(plugin)
            except ValueError as e:
                # Conflict with a builtin or another user plugin
                import sys
                sys.stderr.write(f"[flaura] {e}\n")

        self._layout_manager = FlauraLayout(
            get_provider_name=self.provider_name,
            get_thinking=self.is_thinking,
            get_plugin_count=lambda: len(self._registry.list_plugins()),
        )

        self._layout_manager.input_pane.set_command_handler(
            completer=CommandCompleter(self, self._commands),
            executor=self._execute_command,
        )

        self._agent = AgentCore(EchoProvider())

        self._dispatcher = Dispatcher(
            output=self._layout_manager.output_pane,
            registry=self._registry,
            agent=self._agent,
        )
        self._layout_manager.input_pane.on_submit(self._dispatcher.dispatch)

        self._app = Application(
            layout=self._layout_manager.layout,
            key_bindings=create_global_key_bindings(),
            style=_STYLE,
            full_screen=True,
            mouse_support=True,
        )

    # ── command-mode executor ────────────────────────────────────────────

    def _execute_command(self, line: str) -> None:
        result = self._commands.execute(self, line)
        if result:
            self.message(f"{result}\n")

    # ── status-bar callables ─────────────────────────────────────────────

    def provider_name(self) -> str:
        return self._agent.provider.name if self._agent else "—"

    def is_thinking(self) -> bool:
        return self._dispatcher.thinking if self._dispatcher else False

    # ── public API used by command handlers ──────────────────────────────

    def list_plugins(self):
        return self._registry.list_plugins()

    def list_tools(self):
        return self._registry.list_tools()

    def unregister_plugin(self, name: str) -> None:
        self._registry.unregister(name)
        self._app.invalidate()

    def set_vi_mode(self, on: bool) -> None:
        self._app.editing_mode = EditingMode.VI if on else EditingMode.EMACS
        self._app.invalidate()

    def message(self, text: str) -> None:
        self._layout_manager.output_pane.append(text)

    def quit(self) -> None:
        self._app.exit()

    def run(self) -> None:
        self._app.run()
