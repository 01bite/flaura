from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import (
    AgentChunk,
    Message,
    ProviderToolSchema,
    ToolCall,
)
from flaura.plugins.types import ToolResult

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[ToolResult]]


class AgentCore:
    """Provider-agnostic tool-use loop.

    On each call to `run()`:
      1. Build a message list from the system prompt + user input.
      2. Stream chunks from the provider; collect any tool_use calls.
      3. If the model called tools, execute them, append tool results as
         `role="tool"` messages, then re-invoke the provider.
      4. Repeat until the model produces a turn with zero tool calls, or
         until `max_tool_calls` is reached.

    The dispatcher only sees `text_delta` (model text), `tool_use` (announces
    the call), `tool_result` (result of the call), and a single `done` at the
    very end of the whole loop.
    """

    DEFAULT_MAX_TOOL_CALLS = 25

    def __init__(
        self,
        provider: AgentProvider,
        tool_executor: ToolExecutor | None = None,
        max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
    ) -> None:
        self._provider = provider
        self._executor = tool_executor
        self._max_tool_calls = max_tool_calls

    @property
    def provider(self) -> AgentProvider:
        return self._provider

    def set_tool_executor(self, executor: ToolExecutor) -> None:
        self._executor = executor

    async def run(
        self,
        user_input: str,
        tools: list[ProviderToolSchema] | None = None,
        system: str = "",
    ) -> AsyncIterator[AgentChunk]:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=user_input))

        tool_calls_made = 0

        while True:
            assistant_text = ""
            pending_calls: list[ToolCall] = []

            async for chunk in self._provider.run(messages=messages, tools=tools):
                if chunk.type == "text_delta":
                    assistant_text += chunk.text
                    yield chunk
                elif chunk.type == "tool_use":
                    call = ToolCall(
                        id=chunk.tool_use_id or f"call_{tool_calls_made + len(pending_calls)}",
                        name=chunk.tool_name,
                        arguments=chunk.tool_args,
                    )
                    pending_calls.append(call)
                    yield AgentChunk(
                        type="tool_use",
                        tool_name=call.name,
                        tool_args=call.arguments,
                        tool_use_id=call.id,
                    )
                elif chunk.type == "done":
                    # End of one model turn; loop logic below decides whether to continue.
                    pass

            if not pending_calls:
                yield AgentChunk(type="done")
                return

            messages.append(
                Message(
                    role="assistant",
                    content=assistant_text,
                    tool_calls=pending_calls,
                )
            )

            if self._executor is None:
                # No executor wired; surface results as errors and stop.
                for call in pending_calls:
                    yield AgentChunk(
                        type="tool_result",
                        tool_name=call.name,
                        tool_use_id=call.id,
                        text="no tool executor configured",
                        is_error=True,
                    )
                yield AgentChunk(type="done")
                return

            for call in pending_calls:
                tool_calls_made += 1
                if tool_calls_made > self._max_tool_calls:
                    yield AgentChunk(
                        type="tool_result",
                        tool_name=call.name,
                        tool_use_id=call.id,
                        text=(
                            f"aborted: agent exceeded {self._max_tool_calls} "
                            f"tool calls in one turn"
                        ),
                        is_error=True,
                    )
                    yield AgentChunk(type="done")
                    return

                result = await self._executor(call.name, call.arguments)
                yield AgentChunk(
                    type="tool_result",
                    tool_name=call.name,
                    tool_use_id=call.id,
                    text=_stringify(result.content),
                    is_error=result.is_error,
                )
                messages.append(
                    Message(
                        role="tool",
                        content=_stringify(result.content),
                        tool_call_id=call.id,
                        tool_name=call.name,
                    )
                )


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        import json

        return json.dumps(value, default=str)
    except Exception:
        return str(value)
