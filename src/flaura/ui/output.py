from __future__ import annotations

from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl


class OutputPane:
    def __init__(self) -> None:
        self._text = "display on output plane"
        self.control = FormattedTextControl(text=lambda: self._text)
        self.window = Window(
            content=self.control,
            wrap_lines=True,
        )

    def append(self, text: str) -> None:
        self._text += text
