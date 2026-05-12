from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator

from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import AgentChunk, Message, ProviderToolSchema


class EchoProvider(AgentProvider):
    """Dev/test provider that echoes the latest user message character-by-character.

    Simulates a real provider's TTFT delay before the first chunk so the
    `[thinking]` indicator and mid-stream cancellation are observable.
    """

    name = "echo"

    def __init__(
        self,
        delay_ms: int = 20,
        ttft_min_s: float = 5.0,
        ttft_max_s: float = 10.0,
    ) -> None:
        self._delay = delay_ms / 1000.0
        self._ttft_min = ttft_min_s
        self._ttft_max = ttft_max_s

    async def run(
        self,
        messages: list[Message],
        tools: list[ProviderToolSchema] | None = None,
    ) -> AsyncIterator[AgentChunk]:
        text = ""
        for m in reversed(messages):
            if m.role == "user":
                text = m.content
                break

        ttft = random.uniform(self._ttft_min, self._ttft_max)
        await asyncio.sleep(ttft)

        for ch in text:
            yield AgentChunk(type="text_delta", text=ch)
            if self._delay:
                await asyncio.sleep(self._delay)
        yield AgentChunk(type="done")
