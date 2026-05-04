from __future__ import annotations

from typing import TYPE_CHECKING

from flaura.plugins.base import PromptPlugin

if TYPE_CHECKING:
    from flaura.ui.output import OutputPane


class DefaultPlugin(PromptPlugin):
    name = "default"

    def __init__(self, output: OutputPane) -> None:
        self._output = output

    def on_submit(self, text: str) -> None:
        from flaura.core.dispatcher import CommandAnalysis

        CommandAnalysis(text, self._output)

    def get_title(self) -> str:
        return "default"
