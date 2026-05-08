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
    get_provider_name: Callable[[], str],
    get_thinking: Callable[[], bool],
) -> Window:
    def _text() -> StyleAndTextTuples:
        try:
            cols = get_app().output.get_size().columns
            vi_on = get_app().editing_mode == EditingMode.VI
        except Exception:
            cols = 80
            vi_on = False

        plugin = get_plugin_name()
        provider = get_provider_name()
        thinking = get_thinking()

        left = f"flaura · {plugin} · {provider}"
        thinking_part = " [thinking] " if thinking else ""
        vi_part = " [vi] " if vi_on else ""

        if get_mode() == "single":
            right = " SINGLE "
            right_style = "class:mode.single"
        else:
            right = " MULTI "
            right_style = "class:mode.multi"

        used = len(left) + len(thinking_part) + len(vi_part) + len(right)
        padding = max(0, cols - used)

        return [
            ("class:status-bar", left),
            ("class:status-bar.thinking", thinking_part),
            ("class:status-bar", " " * padding),
            ("class:status-bar.vi", vi_part),
            (right_style, right),
        ]

    return Window(
        content=FormattedTextControl(text=_text),
        height=1,
        style="class:status-bar",
    )
