from __future__ import annotations

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import has_completions
from prompt_toolkit.layout import ConditionalContainer, Float, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.menus import CompletionsMenu


def create_completion_float() -> Float:
    """Popup completion menu anchored to the cursor position."""
    return Float(
        xcursor=True,
        ycursor=True,
        content=CompletionsMenu(max_height=12, scroll_offset=1),
    )


def create_completion_toolbar() -> ConditionalContainer:
    """Single-line toolbar at the bottom, visible only when completions exist."""

    def _text():
        try:
            state = get_app().current_buffer.complete_state
        except Exception:
            return []
        if state is None:
            return []
        items = []
        for i, c in enumerate(state.completions[:12]):
            is_selected = i == state.complete_index
            style = "class:completion-toolbar.current" if is_selected else "class:completion-toolbar.item"
            items.append((style, f" {c.text} "))
            items.append(("class:completion-toolbar.separator", "│"))
        return items[:-1]  # drop trailing separator

    return ConditionalContainer(
        content=Window(
            content=FormattedTextControl(text=_text),
            height=1,
            style="class:completion-toolbar",
        ),
        filter=has_completions,
    )
