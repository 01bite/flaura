from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl


def create_status_bar(get_mode: Callable[[], str]) -> Window:
    def _text() -> StyleAndTextTuples:
        try:
            cols = get_app().output.get_size().columns
        except Exception:
            cols = 80

        left = "flaura · main"

        if get_mode() == "prompt":
            right = " SINGLE "
            right_style = "class:mode.single"
        else:
            right = " MULTI "
            right_style = "class:mode.multi"

        padding = max(0, cols - len(left) - len(right))

        return [
            ("class:status-bar", left + " " * padding),
            (right_style, right),
        ]

    return Window(
        content=FormattedTextControl(text=_text),
        height=1,
        style="class:status-bar",
    )
