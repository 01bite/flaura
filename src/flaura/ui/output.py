from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.processors import (
    HighlightIncrementalSearchProcessor,
    HighlightSearchProcessor,
)

if TYPE_CHECKING:
    from prompt_toolkit.layout.controls import SearchBufferControl


class OutputPane:
    def __init__(self, search_buffer_control: SearchBufferControl | None = None) -> None:
        self.buffer = Buffer(name="output")
        processors = []
        if search_buffer_control is not None:
            processors = [
                HighlightSearchProcessor(),
                HighlightIncrementalSearchProcessor(),
            ]
        self.control = BufferControl(
            buffer=self.buffer,
            focusable=False,
            search_buffer_control=search_buffer_control,
            input_processors=processors,
        )
        self.window = Window(content=self.control, wrap_lines=True)

    def append(self, text: str) -> None:
        new_text = self.buffer.text + text
        self.buffer.set_document(Document(new_text, len(new_text)))
