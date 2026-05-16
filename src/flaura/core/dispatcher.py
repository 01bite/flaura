from __future__ import annotations

import asyncio
import hashlib
from typing import TYPE_CHECKING

from prompt_toolkit.application.current import get_app

if TYPE_CHECKING:
    from flaura.agent.core import AgentCore
    from flaura.knowledge.graph import KnowledgeGraph
    from flaura.plugins.registry import PluginRegistry
    from flaura.ui.output import OutputPane


class Dispatcher:
    def __init__(
        self,
        output: OutputPane,
        registry: PluginRegistry,
        agent: AgentCore,
        knowledge: KnowledgeGraph | None = None,
    ) -> None:
        self._output = output
        self._registry = registry
        self._agent = agent
        self._knowledge = knowledge
        self._current_task: asyncio.Task | None = None
        self._thinking = False
        self._agent.set_tool_executor(self._make_executor())

    @property
    def thinking(self) -> bool:
        return self._thinking

    @property
    def agent(self) -> AgentCore:
        return self._agent

    @agent.setter
    def agent(self, value: AgentCore) -> None:
        self._agent = value
        self._agent.set_tool_executor(self._make_executor())

    def _make_executor(self):
        registry = self._registry
        knowledge = self._knowledge

        async def executor(name: str, args: dict):
            result = await registry.execute_tool_async(name, args)
            if knowledge and not result.is_error:
                tool = registry.get_tool(name)
                if tool and tool.plugin_name:
                    plugin = registry._plugins.get(tool.plugin_name)
                    if plugin:
                        nodes, edges = plugin.extract_knowledge(str(result.content))
                        if nodes or edges:
                            await asyncio.to_thread(knowledge.add_patch, nodes, edges)
            return result

        return executor

    def dispatch(self, text: str) -> None:
        if self._current_task is not None and not self._current_task.done():
            self._current_task.cancel()

        try:
            app = get_app()
            self._current_task = app.create_background_task(self._run(text))
        except Exception as e:
            self._output.append(f"[dispatch error: {e}]\n")
            self._invalidate()

    def _knowledge_context(self, text: str) -> str:
        if not self._knowledge:
            return ""
        from flaura.knowledge.format import format_context
        from flaura.knowledge.query import query as kg_query
        bundle = kg_query(self._knowledge, text)
        ctx = format_context(bundle)
        return f"Known facts:\n{ctx}" if ctx else ""

    def _record_turn(self, user_text: str, assistant_text: str) -> None:
        if not self._knowledge:
            return
        topic_id = "topic_" + hashlib.md5(user_text.encode()).hexdigest()[:12]
        nodes = [
            {"id": topic_id, "label": user_text[:200], "file_type": "concept", "source_file": "user_input"},
        ]
        edges = []
        if assistant_text.strip():
            response_id = "response_" + hashlib.md5(assistant_text.encode()).hexdigest()[:12]
            nodes.append(
                {"id": response_id, "label": assistant_text[:200], "file_type": "concept", "source_file": "llm_response"}
            )
            edges.append(
                {"source": topic_id, "target": response_id, "relation": "answered_by", "confidence": "EXTRACTED", "source_file": "llm_response"}
            )
        self._knowledge.add_patch(nodes=nodes, edges=edges)

    async def _run(self, text: str) -> None:
        my_task = asyncio.current_task()
        self._thinking = True
        self._invalidate()

        self._output.append(f"> {text}\n")
        self._invalidate()

        system = await asyncio.to_thread(self._knowledge_context, text)

        try:
            try:
                tools = self._registry.get_tool_schemas()
                assistant_text = ""
                async for chunk in self._agent.run(text, tools=tools, system=system):
                    if chunk.type == "text_delta":
                        assistant_text += chunk.text
                        if self._thinking:
                            self._thinking = False
                            self._invalidate()
                        self._output.append(chunk.text)
                        self._invalidate()
                    elif chunk.type == "tool_use":
                        self._output.append(
                            f"\n[tool_use: {chunk.tool_name}] {chunk.tool_args}\n"
                        )
                        self._invalidate()
                    elif chunk.type == "tool_result":
                        marker = "tool_error" if chunk.is_error else "tool_result"
                        self._output.append(
                            f"[{marker}: {chunk.tool_name}] {chunk.text}\n"
                        )
                        self._invalidate()
                    elif chunk.type == "done":
                        self._output.append("\n")
                        self._invalidate()
                await asyncio.to_thread(self._record_turn, text, assistant_text)
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
