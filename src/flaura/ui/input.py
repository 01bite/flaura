from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import DynamicCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import PromptMargin
from prompt_toolkit.lexers import DynamicLexer
from prompt_toolkit.search import start_search

from flaura.core.history import get_history_path

if TYPE_CHECKING:
    from prompt_toolkit.layout.controls import BufferControl as _BC

    from flaura.plugins.registry import PluginRegistry

SubmitCallback = Callable[[str], None]
OpenOverlay = Callable[[], None]


class InputPane:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry
        self._on_submit: SubmitCallback | None = None
        self._search_target: _BC | None = None
        self._open_overlay: OpenOverlay | None = None

        self.buffer = Buffer(
            name="input",
            multiline=True,  # needed so newlines (from Shift+Enter, paste) survive in the buffer
            accept_handler=self._on_accept,
            history=FileHistory(str(get_history_path())),
            completer=DynamicCompleter(lambda: self._registry.active.get_completer()),
        )

        kb = KeyBindings()

        @kb.add("tab")
        def _complete(event) -> None:
            event.current_buffer.start_completion(select_first=False)

        @kb.add("c-r")
        def _search(event) -> None:
            if self._search_target is not None:
                start_search(self._search_target)

        # ":" opens the command overlay only when the buffer is empty.
        # Anywhere else, ":" is a literal character.
        @kb.add(":", filter=Condition(lambda: len(self.buffer.text) == 0))
        def _open_command(event) -> None:
            if self._open_overlay is not None:
                self._open_overlay()

        # Plain Enter submits.
        @kb.add("enter")
        def _submit(event) -> None:
            event.current_buffer.validate_and_handle()

        # Alt+Enter / Meta+Enter (Esc then Enter chord) inserts a newline.
        # Terminals can't natively distinguish Shift+Enter from Enter, so this
        # is the universal binding. To use Shift+Enter, configure your terminal
        # to send the same escape sequence (see notes in this file).
        @kb.add("escape", "enter")
        def _newline(event) -> None:
            event.current_buffer.insert_text("\n")

        self.control = BufferControl(
            buffer=self.buffer,
            key_bindings=kb,
            lexer=DynamicLexer(lambda: self._registry.active.get_lexer()),
        )
        self.window = Window(
            content=self.control,
            height=self._height,
            wrap_lines=True,
            left_margins=[
                PromptMargin(
                    get_prompt=lambda: self._registry.active.get_prompt_style().in_prompt(),
                    get_continuation=lambda w, _ln, _wc: self._registry.active.get_prompt_style().in2_prompt(w),
                )
            ],
        )

    def on_submit(self, callback: SubmitCallback) -> None:
        self._on_submit = callback

    def set_search_target(self, control: _BC) -> None:
        self._search_target = control

    def set_open_overlay(self, fn: OpenOverlay) -> None:
        self._open_overlay = fn

    @property
    def mode(self) -> str:
        """Contextual: 'multi' if buffer has newlines, 'single' otherwise."""
        return "multi" if "\n" in self.buffer.text else "single"

    def _on_accept(self, buffer: Buffer) -> bool:
        text = buffer.text
        if text and self._on_submit:
            self._on_submit(text)
        return False

    def _height(self) -> int:
        try:
            rows = get_app().output.get_size().rows
        except Exception:
            rows = 24
        max_h = max(3, rows // 3)
        line_count = self.buffer.text.count("\n") + 1
        return min(line_count, max_h)
