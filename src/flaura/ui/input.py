from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, DynamicCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.margins import PromptMargin
from prompt_toolkit.search import start_search

from flaura.core.history import get_history_path
from flaura.ui.prompt_style import DefaultPrompt

if TYPE_CHECKING:
    from prompt_toolkit.layout.controls import BufferControl as _BC

SubmitCallback = Callable[[str], None]
CommandExecutor = Callable[[str], None]


class InputPane:
    def __init__(self) -> None:
        self._on_submit: SubmitCallback | None = None
        self._search_target: _BC | None = None

        # Command mode state
        self._command_mode: bool = False
        self._command_completer: Completer | None = None
        self._command_executor: CommandExecutor | None = None

        # Input mode: "normal" (Enter submits) | "multi" (Enter inserts newline).
        # Toggled with Esc.
        self._input_mode: str = "normal"

        self._default_prompt = DefaultPrompt()

        self.buffer = Buffer(
            name="input",
            multiline=True,
            accept_handler=self._on_accept,
            history=FileHistory(str(get_history_path())),
            completer=DynamicCompleter(self._active_completer),
        )

        kb = KeyBindings()

        @kb.add("tab")
        def _complete(event) -> None:
            buf = event.current_buffer
            if buf.complete_state:
                buf.complete_next()
            else:
                buf.start_completion(select_first=True)

        @kb.add("s-tab")
        def _complete_back(event) -> None:
            buf = event.current_buffer
            if buf.complete_state:
                buf.complete_previous()

        @kb.add("c-r")
        def _search(event) -> None:
            if self._search_target is not None:
                start_search(self._search_target)

        @kb.add(":", filter=Condition(lambda: not self._command_mode and len(self.buffer.text) == 0))
        def _enter_command_mode(event) -> None:
            self._command_mode = True
            event.app.invalidate()

        @kb.add("escape", filter=Condition(lambda: self._command_mode), eager=True)
        def _exit_command_mode(event) -> None:
            self._command_mode = False
            event.current_buffer.text = ""
            event.app.invalidate()

        @kb.add(
            "backspace",
            filter=Condition(lambda: self._command_mode and len(self.buffer.text) == 0),
        )
        def _backspace_exit(event) -> None:
            self._command_mode = False
            event.app.invalidate()

        @kb.add("escape", filter=Condition(lambda: not self._command_mode), eager=True)
        def _toggle_input_mode(event) -> None:
            self._input_mode = "multi" if self._input_mode == "normal" else "normal"
            event.app.invalidate()

        @kb.add("enter")
        def _on_enter(event) -> None:
            if self._command_mode or self._input_mode == "normal":
                event.current_buffer.validate_and_handle()
            else:
                event.current_buffer.insert_text("\n")

        self.control = BufferControl(buffer=self.buffer, key_bindings=kb)
        self.window = Window(
            content=self.control,
            height=self._height,
            wrap_lines=True,
            left_margins=[
                PromptMargin(
                    get_prompt=self._active_prompt,
                    get_continuation=lambda w, _ln, _wc: self._default_prompt.in2_prompt(w),
                )
            ],
        )

    # ── public wiring ─────────────────────────────────────────────────────

    def on_submit(self, callback: SubmitCallback) -> None:
        self._on_submit = callback

    def set_search_target(self, control: _BC) -> None:
        self._search_target = control

    def set_command_handler(self, completer: Completer, executor: CommandExecutor) -> None:
        self._command_completer = completer
        self._command_executor = executor

    @property
    def mode(self) -> str:
        return self._input_mode

    @property
    def command_mode(self) -> bool:
        return self._command_mode

    # ── mode-aware delegates ──────────────────────────────────────────────

    def _active_completer(self) -> Completer | None:
        return self._command_completer if self._command_mode else None

    def _active_prompt(self):
        if self._command_mode:
            return [("class:command-prompt", ": ")]
        return self._default_prompt.in_prompt()

    # ── submit routing ────────────────────────────────────────────────────

    def _on_accept(self, buffer: Buffer) -> bool:
        text = buffer.text
        if self._command_mode:
            self._command_mode = False
            if text and self._command_executor is not None:
                self._command_executor(text)
        else:
            if text and self._on_submit is not None:
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
