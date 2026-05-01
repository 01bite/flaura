from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app

if TYPE_CHECKING:
    from flaura.ui.output import OutputPane


def CommandAnalysis(text: str, output: OutputPane) -> None:
    output.append(f"> {text}\n")


class Dispatcher:
    def __init__(self, output: OutputPane) -> None:
        self._output = output

    def dispatch(self, text: str) -> None:
        CommandAnalysis(text, self._output)
        try:
            get_app().invalidate()
        except Exception:
            pass
