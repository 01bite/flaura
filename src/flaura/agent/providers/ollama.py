from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import AgentChunk, ProviderToolSchema


class OllamaProvider(AgentProvider):
    """Streaming Ollama provider using the official ollama package."""

    def __init__(
        self,
        model: str = "",
        host: str = "http://localhost:11434",
    ) -> None:
        try:
            import ollama
        except ImportError:
            raise ImportError("pip install ollama")

        self._ollama = ollama
        self._client = ollama.AsyncClient(host=host)
        self._model = model
        self.name = f"ollama/{model}" if model else "ollama"

    async def _resolve_model(self) -> str:
        if self._model:
            return self._model
        response = await self._client.list()
        if not response.models:
            raise RuntimeError("no Ollama models found — pull one first: ollama pull <name>")
        resolved = response.models[0].model
        self._model = resolved
        self.name = f"ollama/{resolved}"
        return resolved

    @staticmethod
    def _format_tools(schemas: list[ProviderToolSchema]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": s.name,
                    "description": s.description,
                    "parameters": s.input_schema,
                },
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
        model = await self._resolve_model()

        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_input})
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
        has_tools = bool(tools)
        if has_tools:
            kwargs["tools"] = self._format_tools(tools)

        async def _open_stream(kw: dict[str, Any]):
            # The 400 from Ollama for unsupported tools may surface either
            # on the await (HTTP status check) or on the first __anext__
            # (when the body starts streaming).  Pull the first chunk inside
            # the try so both paths are caught.
            stream = await self._client.chat(**kw)
            it = stream.__aiter__()
            first = await it.__anext__()
            return first, it

        try:
            first, it = await _open_stream(kwargs)
        except self._ollama.ResponseError as e:
            if has_tools and e.status_code == 400:
                kwargs.pop("tools", None)
                first, it = await _open_stream(kwargs)
            else:
                raise

        async def _full_stream():
            yield first
            async for c in it:
                yield c

        async for chunk in _full_stream():
            msg = chunk.message

            if msg.content:
                yield AgentChunk(type="text_delta", text=msg.content)

            for tc in msg.tool_calls or []:
                args: Any = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"_raw": args}
                yield AgentChunk(
                    type="tool_use",
                    tool_name=tc.function.name,
                    tool_args=args,
                    tool_use_id=tc.function.name,
                )

        yield AgentChunk(type="done")
