from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app

if TYPE_CHECKING:
    from flaura.plugins.registry import PluginRegistry
    from flaura.ui.output import OutputPane


def CommandAnalysis(text: str, output: OutputPane) -> None:
    output.append(f"> {text}\n")


class Dispatcher:
    def __init__(self, output: OutputPane, registry: PluginRegistry) -> None:
        self._output = output
        self._registry = registry

    def dispatch(self, text: str) -> None:
        self._registry.active.on_submit(text)
        try:
            get_app().invalidate()
        except Exception:
            pass
