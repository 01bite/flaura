from __future__ import annotations

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import BufferControl


class OutputPane:
    def __init__(self) -> None:
        self.buffer = Buffer(name="output")
        self.control = BufferControl(buffer=self.buffer, focusable=False)
        self.window = Window(content=self.control, wrap_lines=True)

    def append(self, text: str) -> None:
        new_text = self.buffer.text + text
        self.buffer.set_document(Document(new_text, len(new_text)))
