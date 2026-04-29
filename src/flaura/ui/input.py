from __future__ import annotations

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import BufferControl


class InputPane:
    def __init__(self) -> None:
        self.buffer = Buffer(name="input", multiline=True)
        self.control = BufferControl(buffer=self.buffer)
        self.window = Window(
            content=self.control,
            height=self._height,
            wrap_lines=False,
        )

    def _height(self) -> int:
        try:
            rows = get_app().output.get_size().rows
        except Exception:
            rows = 24
        max_h = max(3, rows // 3)
        line_count = self.buffer.text.count("\n") + 1
        return min(line_count, max_h)
