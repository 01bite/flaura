from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.layout import FloatContainer, HSplit, Layout, Window
from prompt_toolkit.widgets import SearchToolbar

from flaura.ui.completion import create_completion_float
from flaura.ui.input import InputPane
from flaura.ui.output import OutputPane
from flaura.ui.status_bar import create_status_bar


class FlauraLayout:
    def __init__(
        self,
        get_provider_name: Callable[[], str],
        get_thinking: Callable[[], bool],
        get_plugin_count: Callable[[], int],
    ) -> None:
        self.search_toolbar = SearchToolbar()
        self.output_pane = OutputPane(search_buffer_control=self.search_toolbar.control)
        self.input_pane = InputPane()
        self.input_pane.set_search_target(self.output_pane.control)

        separator = Window(height=1, char="─", style="class:separator")

        body = HSplit([
            create_status_bar(
                get_mode=lambda: self.input_pane.mode,
                get_provider_name=get_provider_name,
                get_thinking=get_thinking,
                get_plugin_count=get_plugin_count,
            ),
            self.output_pane.window,
            separator,
            self.input_pane.window,
            self.search_toolbar,
        ])

        self._float_container = FloatContainer(
            content=body,
            floats=[create_completion_float()],
        )

        self._layout = Layout(self._float_container, focused_element=self.input_pane.window)

    @property
    def layout(self) -> Layout:
        return self._layout
