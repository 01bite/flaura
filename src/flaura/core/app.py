from __future__ import annotations

from flaura.agent.core import AgentCore
from flaura.config import FlauraConfig
from flaura.core.commands import make_default_registry
from flaura.knowledge.graph import KnowledgeGraph
from flaura.plugins.builtin import BUILTIN_PLUGINS
from flaura.plugins.loader import discover as discover_plugin_dirs
from flaura.plugins.loader import discover_user_plugins, trust_plugin, untrust_plugin
from flaura.plugins.registry import PluginRegistry


class FlauraApp:
    """Holds long-lived app state: providers, plugin/command registries, knowledge graph.

    Stateless about the UI — the REPL wires a Dispatcher and PromptSession around this.
    """

    def __init__(self, config: FlauraConfig | None = None, debug: bool = False) -> None:
        self._config = config or FlauraConfig.load()
        self._debug = debug

        self._registry = PluginRegistry(tool_timeout_s=self._config.tool_timeout_s)
        self._commands = make_default_registry(debug=debug)

        for plugin_class in BUILTIN_PLUGINS:
            self._registry.register(plugin_class())

        for plugin in discover_user_plugins(app_home=self._config.app_home):
            try:
                self._registry.register(plugin)
            except ValueError as e:
                import sys
                sys.stderr.write(f"[flaura] {e}\n")

        self._agent: AgentCore = self._make_provider(self._config.provider)
        self._knowledge = KnowledgeGraph(self._config.app_home / "knowledge" / "graph.json")
        self._quit = False

    # ── provider factory ─────────────────────────────────────────────────────

    def _make_provider(self, name: str, model: str | None = None) -> AgentCore:
        if name == "ollama":
            from flaura.agent.providers.ollama import OllamaProvider
            provider = OllamaProvider(
                model=model or self._config.ollama_model,
                host=self._config.ollama_host,
            )
        else:
            from flaura.agent.providers.echo import EchoProvider
            provider = EchoProvider()
        return AgentCore(
            provider,
            max_tool_calls=self._config.max_tool_calls_per_turn,
        )

    # ── accessors ────────────────────────────────────────────────────────────

    @property
    def config(self) -> FlauraConfig:
        return self._config

    @property
    def debug(self) -> bool:
        return self._debug

    @property
    def agent(self) -> AgentCore:
        return self._agent

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    @property
    def commands(self):
        return self._commands

    @property
    def knowledge(self) -> KnowledgeGraph:
        return self._knowledge

    def provider_name(self) -> str:
        return self._agent.provider.name if self._agent else "—"

    def should_quit(self) -> bool:
        return self._quit

    # ── public API used by command handlers ──────────────────────────────────

    def list_plugins(self):
        return self._registry.list_plugins()

    def ollama_host(self) -> str:
        return self._config.ollama_host

    def list_tools(self):
        return self._registry.list_tools()

    def execute_tool(self, name: str, args: dict):
        return self._registry.execute_tool(name, args)

    def unregister_plugin(self, name: str) -> None:
        self._registry.unregister(name)

    def create_plugin(self, name: str):
        from flaura.plugins.loader import create_plugin_scaffold
        return create_plugin_scaffold(name, app_home=self._config.app_home)

    def discovered_plugins(self):
        return discover_plugin_dirs(app_home=self._config.app_home)

    def trust_plugin(self, name: str) -> None:
        trust_plugin(name, app_home=self._config.app_home)

    def untrust_plugin(self, name: str) -> None:
        untrust_plugin(name, app_home=self._config.app_home)

    def set_provider(self, provider_name: str, model: str | None = None) -> str:
        """Switch the active agent provider. Returns the new provider label."""
        self._agent = self._make_provider(provider_name, model=model)
        return self._agent.provider.name

    def quit(self) -> None:
        self._quit = True

    # ── run ──────────────────────────────────────────────────────────────────

    def run(self) -> None:
        import asyncio

        from flaura.core.repl import Repl

        asyncio.run(Repl(self).run())
