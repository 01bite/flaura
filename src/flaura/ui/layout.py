from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.layout import FloatContainer, HSplit, Layout, Window
from prompt_toolkit.widgets import SearchToolbar

from flaura.ui.completion import create_completion_float, create_completion_toolbar
from flaura.ui.input import InputPane
from flaura.ui.output import OutputPane
from flaura.ui.status_bar import create_status_bar

if TYPE_CHECKING:
    from flaura.plugins.registry import PluginRegistry
    from flaura.ui.command_line import CommandOverlay


class FlauraLayout:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

        self.search_toolbar = SearchToolbar()
        self.output_pane = OutputPane(search_buffer_control=self.search_toolbar.control)
        self.input_pane = InputPane(registry)
        self.input_pane.set_search_target(self.output_pane.control)

        separator = Window(height=1, char="─", style="class:separator")

        body = HSplit([
            create_status_bar(
                get_mode=lambda: self.input_pane.mode.value,
                get_plugin_name=lambda: self._registry.active.get_title(),
            ),
            self.output_pane.window,
            separator,
            self.input_pane.window,
            create_completion_toolbar(),
            self.search_toolbar,
        ])

        self._float_container = FloatContainer(
            content=body,
            floats=[create_completion_float()],
        )

        self._layout = Layout(self._float_container, focused_element=self.input_pane.window)

    def attach_command_overlay(self, overlay: CommandOverlay) -> None:
        self._float_container.floats.append(overlay.make_float())
        self.input_pane.set_open_overlay(overlay.show)

    @property
    def layout(self) -> Layout:
        return self._layout
