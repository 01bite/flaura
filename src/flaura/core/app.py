from __future__ import annotations

from prompt_toolkit import Application
from prompt_toolkit.styles import Style

from flaura.core.dispatcher import Dispatcher
from flaura.ui.key_bindings import create_global_key_bindings
from flaura.ui.layout import FlauraLayout

_STYLE = Style.from_dict(
    {
        "status-bar": "bg:#444444 #ffffff bold",
        "separator": "bg:#333333 #555555",
    }
)


class FlauraApp:
    def __init__(self) -> None:
        self._layout_manager = FlauraLayout()
        self._dispatcher = Dispatcher(self._layout_manager.output_pane)
        self._layout_manager.input_pane.on_submit(self._dispatcher.dispatch)

        self._app = Application(
            layout=self._layout_manager.layout,
            key_bindings=create_global_key_bindings(),
            style=_STYLE,
            full_screen=True,
            mouse_support=False,
        )

    def run(self) -> None:
        self._app.run()
