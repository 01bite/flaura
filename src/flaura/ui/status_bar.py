from __future__ import annotations

from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl


def create_status_bar() -> Window:
    return Window(
        content=FormattedTextControl(text="flaura · main"),
        height=1,
        style="class:status-bar",
    )
