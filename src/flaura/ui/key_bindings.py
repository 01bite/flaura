from __future__ import annotations

from prompt_toolkit.key_binding import KeyBindings


def create_global_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("c-c")
    # def _pressed(event):
    #     print("ctrl c pressed")

    @kb.add("c-d")
    def _quit(event) -> None:
        event.app.exit()

    return kb
