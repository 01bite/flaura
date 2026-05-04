from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.application.current import get_app
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl


def create_status_bar(
    get_mode: Callable[[], str],
    get_plugin_name: Callable[[], str],
) -> Window:
    def _text() -> StyleAndTextTuples:
        try:
            cols = get_app().output.get_size().columns
            vi_on = get_app().editing_mode == EditingMode.VI
        except Exception:
            cols = 80
            vi_on = False

        left = f"flaura · {get_plugin_name()}"
        vi_part = " [vi] " if vi_on else ""

        if get_mode() == "prompt":
            right = " SINGLE "
            right_style = "class:mode.single"
        else:
            right = " MULTI "
            right_style = "class:mode.multi"

        padding = max(0, cols - len(left) - len(vi_part) - len(right))

        return [
            ("class:status-bar", left + " " * padding),
            ("class:status-bar.vi", vi_part),
            (right_style, right),
        ]

    return Window(
        content=FormattedTextControl(text=_text),
        height=1,
        style="class:status-bar",
    )
