from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app

if TYPE_CHECKING:
    from flaura.agent.core import AgentCore
    from flaura.plugins.registry import PluginRegistry
    from flaura.ui.output import OutputPane


class Dispatcher:
    def __init__(
        self,
        output: OutputPane,
        registry: PluginRegistry,
        agent: AgentCore,
    ) -> None:
        self._output = output
        self._registry = registry
        self._agent = agent
        self._current_task: asyncio.Task | None = None
        self._thinking = False

    @property
    def thinking(self) -> bool:
        return self._thinking

    def dispatch(self, text: str) -> None:
        if self._current_task is not None and not self._current_task.done():
            self._current_task.cancel()

        try:
            app = get_app()
            self._current_task = app.create_background_task(self._run(text))
        except Exception as e:
            self._output.append(f"[dispatch error: {e}]\n")
            self._invalidate()

    async def _run(self, text: str) -> None:
        my_task = asyncio.current_task()
        self._thinking = True
        self._invalidate()

        # Echo the user's input
        self._output.append(f"> {text}\n")
        self._invalidate()

        try:
            try:
                tools = self._registry.get_tool_schemas()
                async for chunk in self._agent.run(text, tools=tools):
                    if chunk.type == "text_delta":
                        if self._thinking:
                            self._thinking = False
                            self._invalidate()
                        self._output.append(chunk.text)
                        self._invalidate()
                    elif chunk.type == "tool_use":
                        # Run the requested tool through the registry
                        result = self._registry.execute_tool(
                            chunk.tool_name, chunk.tool_args
                        )
                        marker = "tool_error" if result.is_error else "tool"
                        self._output.append(
                            f"\n[{marker}: {chunk.tool_name}] {result.content}\n"
                        )
                        self._invalidate()
                        # Phase 9 will send the result back to the provider
                    elif chunk.type == "done":
                        self._output.append("\n")
                        self._invalidate()
            except asyncio.CancelledError:
                self._output.append("\n[cancelled]\n")
                self._invalidate()
                raise
            except Exception as e:
                self._output.append(f"\n[agent error: {e}]\n")
                self._invalidate()
        finally:
            if asyncio.current_task() is self._current_task or my_task is self._current_task:
                self._thinking = False
                self._invalidate()

    def _invalidate(self) -> None:
        try:
            get_app().invalidate()
        except Exception:
            pass
