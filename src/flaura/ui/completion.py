from __future__ import annotations

from prompt_toolkit.layout import Float
from prompt_toolkit.layout.menus import CompletionsMenu


def create_completion_float() -> Float:
    """Popup completion menu anchored to the cursor position."""
    return Float(
        xcursor=True,
        ycursor=True,
        content=CompletionsMenu(max_height=12, scroll_offset=1),
    )
