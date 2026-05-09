from __future__ import annotations

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.styles import Style

from flaura.agent.core import AgentCore
from flaura.config import FlauraConfig
from flaura.core.commands import make_default_registry
from flaura.core.dispatcher import Dispatcher
from flaura.plugins.builtin import BUILTIN_PLUGINS
from flaura.plugins.loader import discover_user_plugins
from flaura.plugins.registry import PluginRegistry
from flaura.ui.command_line import CommandCompleter
from flaura.ui.key_bindings import create_global_key_bindings
from flaura.ui.layout import FlauraLayout


class FlauraApp:
    def __init__(self, config: FlauraConfig | None = None) -> None:
        self._config = config or FlauraConfig.load()
        self._agent: AgentCore | None = None
        self._dispatcher: Dispatcher | None = None

        self._registry = PluginRegistry()
        self._commands = make_default_registry()

        for plugin_class in BUILTIN_PLUGINS:
            self._registry.register(plugin_class())

        for plugin in discover_user_plugins(app_home=self._config.app_home):
            try:
                self._registry.register(plugin)
            except ValueError as e:
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

        self._agent = self._make_provider(self._config.provider)

        if self._config.vi_mode:
            # Applied after Application is created — stored for __init__ order
            self._start_in_vi = True
        else:
            self._start_in_vi = False

        self._dispatcher = Dispatcher(
            output=self._layout_manager.output_pane,
            registry=self._registry,
            agent=self._agent,
        )
        self._layout_manager.input_pane.on_submit(self._dispatcher.dispatch)

        self._app = Application(
            layout=self._layout_manager.layout,
            key_bindings=create_global_key_bindings(),
            style=Style.from_dict(self._config.colors),
            full_screen=True,
            mouse_support=True,
            editing_mode=EditingMode.VI if self._config.vi_mode else EditingMode.EMACS,
        )

    # ── provider factory ─────────────────────────────────────────────────────

    def _make_provider(self, name: str, model: str | None = None) -> AgentCore:
        if name == "ollama":
            from flaura.agent.providers.ollama import OllamaProvider
            return AgentCore(OllamaProvider(
                model=model or self._config.ollama_model,
                host=self._config.ollama_host,
            ))
        # default / "echo"
        from flaura.agent.providers.echo import EchoProvider
        return AgentCore(EchoProvider())

    # ── command-mode executor ────────────────────────────────────────────────

    def _execute_command(self, line: str) -> None:
        result = self._commands.execute(self, line)
        if result:
            self.message(f"{result}\n")

    # ── status-bar callables ─────────────────────────────────────────────────

    def provider_name(self) -> str:
        return self._agent.provider.name if self._agent else "—"

    def is_thinking(self) -> bool:
        return self._dispatcher.thinking if self._dispatcher else False

    # ── public API used by command handlers ──────────────────────────────────

    def list_plugins(self):
        return self._registry.list_plugins()

    def ollama_host(self) -> str:
        return self._config.ollama_host

    def list_tools(self):
        return self._registry.list_tools()

    def unregister_plugin(self, name: str) -> None:
        self._registry.unregister(name)
        self._app.invalidate()

    def set_vi_mode(self, on: bool) -> None:
        self._app.editing_mode = EditingMode.VI if on else EditingMode.EMACS
        self._app.invalidate()

    def set_provider(self, provider_name: str, model: str | None = None) -> str:
        """Switch the active agent provider. Returns the new provider label."""
        self._agent = self._make_provider(provider_name, model=model)
        self._dispatcher.agent = self._agent
        self._app.invalidate()
        return self._agent.provider.name

    def message(self, text: str) -> None:
        self._layout_manager.output_pane.append(text)

    def quit(self) -> None:
        self._app.exit()

    def run(self) -> None:
        self._app.run()
