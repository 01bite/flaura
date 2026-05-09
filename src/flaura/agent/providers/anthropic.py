from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import AgentChunk, ProviderToolSchema


class AnthropicProvider(AgentProvider):
    """Streaming Anthropic provider via the official SDK."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 8096,
        api_key: str | None = None,
    ) -> None:
        try:
            import anthropic as _sdk
        except ImportError:
            raise ImportError("pip install anthropic")

        self._client = _sdk.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

        # Friendly label for the status bar: "sonnet-4-6", "opus-4-7", etc.
        tag = model.removeprefix("claude-")
        self.name = f"anthropic/{tag}"

    def format_tools(self, schemas: list[ProviderToolSchema]) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "input_schema": s.input_schema,
            }
            for s in schemas
        ]

    async def run(
        self,
        user_input: str,
        context: str = "",
        tools: list[ProviderToolSchema] | None = None,
        system: str = "",
    ) -> AsyncIterator[AgentChunk]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": user_input}],
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self.format_tools(tools)

        tool_block: dict[str, Any] | None = None
        tool_json_parts: list[str] = []

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                etype = event.type

                if etype == "content_block_start":
                    cb = event.content_block
                    if cb.type == "tool_use":
                        tool_block = {"name": cb.name, "id": cb.id}
                        tool_json_parts = []
                    else:
                        tool_block = None

                elif etype == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield AgentChunk(type="text_delta", text=delta.text)
                    elif delta.type == "input_json_delta" and tool_block is not None:
                        tool_json_parts.append(delta.partial_json)

                elif etype == "content_block_stop":
                    if tool_block is not None:
                        raw = "".join(tool_json_parts)
                        try:
                            args = json.loads(raw) if raw else {}
                        except json.JSONDecodeError:
                            args = {"_raw": raw}
                        yield AgentChunk(
                            type="tool_use",
                            tool_name=tool_block["name"],
                            tool_args=args,
                            tool_use_id=tool_block["id"],
                        )
                        tool_block = None
                        tool_json_parts = []

        yield AgentChunk(type="done")
