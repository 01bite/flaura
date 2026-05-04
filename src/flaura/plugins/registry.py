from __future__ import annotations

from flaura.plugins.base import PromptPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, PromptPlugin] = {}
        self._active: str | None = None

    def register(self, plugin: PromptPlugin) -> None:
        self._plugins[plugin.name] = plugin
        if self._active is None:
            self._active = plugin.name

    def get(self, name: str) -> PromptPlugin:
        return self._plugins[name]

    def list(self) -> list[str]:
        return list(self._plugins.keys())

    def set_active(self, name: str) -> None:
        if name not in self._plugins:
            raise KeyError(f"No plugin named {name!r}")
        self._active = name

    @property
    def active(self) -> PromptPlugin:
        if self._active is None:
            raise RuntimeError("No active plugin — register at least one plugin first")
        return self._plugins[self._active]
