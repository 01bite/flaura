from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import PromptMargin

from flaura.core.history import get_history_path
from flaura.ui.prompt_style import DefaultPrompt

SubmitCallback = Callable[[str], None]


class InputPane:
    def __init__(self) -> None:
        self._on_submit: SubmitCallback | None = None
        self._prompt_style = DefaultPrompt()

        self.buffer = Buffer(
            name="input",
            multiline=True,
            accept_handler=self._on_accept,
            history=FileHistory(str(get_history_path())),
        )

        kb = KeyBindings()

        @kb.add("enter")
        def _newline(event) -> None:
            event.current_buffer.insert_text("\n")

        @kb.add("escape", "enter")
        def _submit(event) -> None:
            event.current_buffer.validate_and_handle()

        self.control = BufferControl(buffer=self.buffer, key_bindings=kb)
        self.window = Window(
            content=self.control,
            height=self._height,
            wrap_lines=True,
            left_margins=[
                PromptMargin(
                    get_prompt=self._prompt_style.in_prompt,
                    get_continuation=lambda w, _ln, _wc: self._prompt_style.in2_prompt(w),
                )
            ],
        )

    def on_submit(self, callback: SubmitCallback) -> None:
        self._on_submit = callback

    def _on_accept(self, buffer: Buffer) -> bool:
        text = buffer.text
        if text and self._on_submit:
            self._on_submit(text)
        return False  # False = clear the buffer after handling

    def _height(self) -> int:
        try:
            rows = get_app().output.get_size().rows
        except Exception:
            rows = 24
        max_h = max(3, rows // 3)
        line_count = self.buffer.text.count("\n") + 1
        return min(line_count, max_h)
