from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import AgentChunk, ProviderToolSchema


class OllamaProvider(AgentProvider):
    """Streaming Ollama provider — talks to a local Ollama server over HTTP."""

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
    ) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("pip install httpx")

        self._httpx = httpx
        self._model = model
        self._host = host.rstrip("/")
        self.name = f"ollama/{model}"

    def format_tools(self, schemas: list[ProviderToolSchema]) -> list[dict[str, Any]]:
        # Ollama follows OpenAI's tool schema.
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
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_input})

        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = self.format_tools(tools)

        url = f"{self._host}/api/generate"

        async with self._httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk.get("message", {})

                    text = msg.get("content", "")
                    if text:
                        yield AgentChunk(type="text_delta", text=text)

                    # Ollama emits tool_calls as a complete object (not streamed
                    # piecewise like Anthropic).  Each call has function.name +
                    # function.arguments (dict; may rarely be a JSON string).
                    for tc in msg.get("tool_calls") or []:
                        fn = tc.get("function", {})
                        args = fn.get("arguments") or {}
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {"_raw": args}
                        yield AgentChunk(
                            type="tool_use",
                            tool_name=fn.get("name", ""),
                            tool_args=args,
                            # Ollama doesn't supply tool_use IDs; reuse the name.
                            tool_use_id=fn.get("name", ""),
                        )

                    if chunk.get("done"):
                        break

        yield AgentChunk(type="done")
