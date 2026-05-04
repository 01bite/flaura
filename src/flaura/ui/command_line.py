from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, Float, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl

if TYPE_CHECKING:
    from flaura.core.app import FlauraApp
    from flaura.core.commands import CommandRegistry


class CommandCompleter(Completer):
    """Completes :command names + per-command argument completions (live)."""

    def __init__(self, app: FlauraApp, commands: CommandRegistry) -> None:
        self._app = app
        self._commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.split(" ", 1)

        if len(parts) == 1:
            prefix = parts[0]
            for name in self._commands.names():
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))
            return

        cmd, rest = parts[0], parts[1]
        if cmd == "set":
            for opt in ("vi", "novi"):
                if opt.startswith(rest):
                    yield Completion(opt, start_position=-len(rest))
        elif cmd == "plugin":
            for name in self._app.list_plugins():
                if name.startswith(rest):
                    yield Completion(name, start_position=-len(rest))


class CommandOverlay:
    def __init__(
        self,
        app: FlauraApp,
        commands: CommandRegistry,
        return_focus_to: Buffer,
    ) -> None:
        self._app = app
        self._commands = commands
        self._return_to = return_focus_to
        self._visible = False

        self.buffer = Buffer(
            name="command",
            accept_handler=self._on_accept,
            completer=CommandCompleter(app, commands),
            multiline=False,
        )

        kb = KeyBindings()

        @kb.add("escape", eager=True)
        def _escape(event) -> None:
            self.hide()

        self.control = BufferControl(buffer=self.buffer, key_bindings=kb)

        prompt_window = Window(
            content=FormattedTextControl(text=":"),
            width=1,
            style="class:command-overlay.prompt",
        )
        input_window = Window(
            content=self.control,
            height=1,
            style="class:command-overlay",
        )

        self._container = ConditionalContainer(
            content=VSplit([prompt_window, input_window]),
            filter=Condition(lambda: self._visible),
        )

    @property
    def visible(self) -> bool:
        return self._visible

    def make_float(self) -> Float:
        return Float(
            content=self._container,
            top=1,
            left=2,
            right=2,
        )

    def show(self) -> None:
        self._visible = True
        self.buffer.text = ""
        get_app().layout.focus(self.buffer)

    def hide(self) -> None:
        self._visible = False
        self.buffer.text = ""
        try:
            get_app().layout.focus(self._return_to)
        except Exception:
            pass

    def _on_accept(self, buffer: Buffer) -> bool:
        result = self._commands.execute(self._app, buffer.text)
        if result:
            self._app.message(f"{result}\n")
        self.hide()
        return False
