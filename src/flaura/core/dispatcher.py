from __future__ import annotations

import asyncio
import hashlib
import time
from typing import TYPE_CHECKING

from flaura.ui.console import Spinner

if TYPE_CHECKING:
    from flaura.agent.core import AgentCore
    from flaura.knowledge.graph import KnowledgeGraph
    from flaura.plugins.registry import PluginRegistry
    from flaura.ui.console import Console


class Dispatcher:
    """Runs one agent turn, streaming output to a Console."""

    def __init__(
        self,
        console: Console,
        registry: PluginRegistry,
        agent: AgentCore,
        knowledge: KnowledgeGraph | None = None,
    ) -> None:
        self._console = console
        self._registry = registry
        self._agent = agent
        self._knowledge = knowledge
        self._last_response = ""
        self._transcript: list[str] = []
        self._agent.set_tool_executor(self._make_executor())

    # ── state ────────────────────────────────────────────────────────────────

    @property
    def last_response(self) -> str:
        return self._last_response

    @property
    def transcript(self) -> str:
        return "\n".join(self._transcript)

    @property
    def agent(self) -> AgentCore:
        return self._agent

    @agent.setter
    def agent(self, value: AgentCore) -> None:
        self._agent = value
        self._agent.set_tool_executor(self._make_executor())

    # ── tool executor ────────────────────────────────────────────────────────

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

    # ── public API ───────────────────────────────────────────────────────────

    async def dispatch(self, text: str) -> None:
        """One full agent turn: stream the response to the console."""
        self._transcript.append(text)
        start = time.monotonic()
        spinner = Spinner()
        spinner.start("thinking")

        try:
            system = await asyncio.to_thread(self._knowledge_context, text)
            tools = self._registry.get_tool_schemas()
            assistant_text = ""
            assistant_started = False
            async for chunk in self._agent.run(text, tools=tools, system=system):
                if chunk.type == "text_delta":
                    if not assistant_started:
                        await spinner.stop()
                        self._console.assistant_prefix()
                        assistant_started = True
                    assistant_text += chunk.text
                    self._console.assistant_chunk(chunk.text)
                elif chunk.type == "tool_use":
                    await spinner.stop()
                    self._console.ensure_newline()
                    self._console.tool_use(chunk.tool_name, chunk.tool_args)
                elif chunk.type == "tool_result":
                    await spinner.stop()
                    self._console.ensure_newline()
                    self._console.tool_result(
                        chunk.tool_name, chunk.text, chunk.is_error
                    )
                elif chunk.type == "done":
                    self._console.ensure_newline()

            self._last_response = assistant_text
            if assistant_text:
                self._transcript.append(assistant_text)
            await asyncio.to_thread(self._record_turn, text, assistant_text)

        except asyncio.CancelledError:
            await spinner.stop()
            self._console.ensure_newline()
            self._console.info("[cancelled]")
            raise
        except Exception as e:
            await spinner.stop()
            self._console.ensure_newline()
            self._console.error(f"agent error: {e}")
        finally:
            await spinner.stop()
            elapsed = time.monotonic() - start
            self._console.ensure_newline()
            self._console.timing(elapsed)

    # ── knowledge graph ──────────────────────────────────────────────────────

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
            {
                "id": topic_id,
                "label": user_text[:200],
                "file_type": "concept",
                "source_file": "user_input",
            },
        ]
        edges = []
        if assistant_text.strip():
            response_id = "response_" + hashlib.md5(assistant_text.encode()).hexdigest()[:12]
            nodes.append(
                {
                    "id": response_id,
                    "label": assistant_text[:200],
                    "file_type": "concept",
                    "source_file": "llm_response",
                }
            )
            edges.append(
                {
                    "source": topic_id,
                    "target": response_id,
                    "relation": "answered_by",
                    "confidence": "EXTRACTED",
                    "source_file": "llm_response",
                }
            )
        self._knowledge.add_patch(nodes=nodes, edges=edges)
