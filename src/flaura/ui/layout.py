from __future__ import annotations

from prompt_toolkit.layout import HSplit, Layout, Window

from flaura.ui.input import InputPane
from flaura.ui.output import OutputPane
from flaura.ui.status_bar import create_status_bar


class FlauraLayout:
    def __init__(self) -> None:
        self.output_pane = OutputPane()
        self.input_pane = InputPane()
        self._layout = self._build()

    def _build(self) -> Layout:
        separator = Window(height=1, char="─", style="class:separator")

        container = HSplit(
            [
                create_status_bar(lambda: self.input_pane.mode.value),
                self.output_pane.window,
                separator,
                self.input_pane.window,
            ]
        )

        return Layout(container, focused_element=self.input_pane.window)

    @property
    def layout(self) -> Layout:
        return self._layout
