from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl


def create_status_bar(
    get_mode: Callable[[], str],
    get_provider_name: Callable[[], str],
    get_thinking: Callable[[], bool],
    get_plugin_count: Callable[[], int],
) -> Window:
    def _text() -> StyleAndTextTuples:
        try:
            cols = get_app().output.get_size().columns
        except Exception:
            cols = 80

        provider = get_provider_name()
        n_plugins = get_plugin_count()
        thinking = get_thinking()

        left = f"flaura · {provider} · {n_plugins} plugins"
        thinking_part = " [thinking] " if thinking else ""

        if get_mode() == "normal":
            right = " NORMAL "
            right_style = "class:mode.normal"
        else:
            right = " MULTI "
            right_style = "class:mode.multi"

        used = len(left) + len(thinking_part) + len(right)
        padding = max(0, cols - used)

        return [
            ("class:status-bar", left),
            ("class:status-bar.thinking", thinking_part),
            ("class:status-bar", " " * padding),
            (right_style, right),
        ]

    return Window(
        content=FormattedTextControl(text=_text),
        height=1,
        style="class:status-bar",
    )
