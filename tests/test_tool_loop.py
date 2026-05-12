from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from flaura.agent.core import AgentCore
from flaura.agent.providers.base import AgentProvider
from flaura.agent.types import AgentChunk, Message, ProviderToolSchema
from flaura.plugins.base import Plugin
from flaura.plugins.registry import PluginRegistry
from flaura.plugins.types import Tool


class _ScriptedProvider(AgentProvider):
    """Provider whose output is scripted per call so we can drive the loop."""

    name = "scripted"

    def __init__(self, scripts: list[list[AgentChunk]]) -> None:
        self._scripts = list(scripts)
        self.calls: list[list[Message]] = []

    async def run(
        self,
        messages: list[Message],
        tools: list[ProviderToolSchema] | None = None,
    ) -> AsyncIterator[AgentChunk]:
        self.calls.append([Message(**m.__dict__) for m in messages])
        if not self._scripts:
            yield AgentChunk(type="done")
            return
        script = self._scripts.pop(0)
        for chunk in script:
            yield chunk


class _AddPlugin(Plugin):
    name = "math"
    description = "math tools"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="add",
                description="add two integers",
                input_schema={
                    "type": "object",
                    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                    "required": ["a", "b"],
                    "additionalProperties": False,
                },
                handler=lambda a, b: a + b,
            ),
        ]


def _collect(agen):
    out: list[AgentChunk] = []

    async def _run():
        async for chunk in agen:
            out.append(chunk)

    asyncio.run(_run())
    return out


def test_loop_handles_simple_text():
    provider = _ScriptedProvider([
        [
            AgentChunk(type="text_delta", text="hi"),
            AgentChunk(type="done"),
        ]
    ])
    core = AgentCore(provider)
    chunks = _collect(core.run("hello"))
    texts = [c.text for c in chunks if c.type == "text_delta"]
    assert texts == ["hi"]
    assert chunks[-1].type == "done"


def test_loop_executes_tool_and_feeds_result_back():
    registry = PluginRegistry()
    registry.register(_AddPlugin())

    provider = _ScriptedProvider([
        # Turn 1: ask for the tool
        [
            AgentChunk(
                type="tool_use",
                tool_name="add",
                tool_args={"a": 2, "b": 3},
                tool_use_id="call_1",
            ),
            AgentChunk(type="done"),
        ],
        # Turn 2: read the result and reply
        [
            AgentChunk(type="text_delta", text="5"),
            AgentChunk(type="done"),
        ],
    ])
    core = AgentCore(provider, tool_executor=registry.execute_tool_async)
    chunks = _collect(core.run("what is 2+3"))

    types = [c.type for c in chunks]
    assert "tool_use" in types
    assert "tool_result" in types
    assert chunks[-1].type == "done"

    result_chunk = next(c for c in chunks if c.type == "tool_result")
    assert result_chunk.text == "5"
    assert not result_chunk.is_error

    # The provider must have seen the tool result message on its second call
    assert len(provider.calls) == 2
    second_call = provider.calls[1]
    tool_msgs = [m for m in second_call if m.role == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].content == "5"
    assert tool_msgs[0].tool_call_id == "call_1"


def test_loop_respects_max_tool_calls():
    registry = PluginRegistry()
    registry.register(_AddPlugin())

    # Provider always asks for another tool call → would loop forever.
    looping_script: list[AgentChunk] = [
        AgentChunk(
            type="tool_use",
            tool_name="add",
            tool_args={"a": 1, "b": 1},
            tool_use_id="x",
        ),
        AgentChunk(type="done"),
    ]
    provider = _ScriptedProvider([list(looping_script) for _ in range(20)])
    core = AgentCore(
        provider,
        tool_executor=registry.execute_tool_async,
        max_tool_calls=3,
    )
    chunks = _collect(core.run("loop please"))
    errors = [c for c in chunks if c.type == "tool_result" and c.is_error]
    assert any("exceeded" in c.text for c in errors)
    assert chunks[-1].type == "done"


def test_tool_timeout_returns_error(monkeypatch):
    registry = PluginRegistry(tool_timeout_s=0.05)

    async def _slow(**_: Any) -> str:  # noqa: ARG001
        await asyncio.sleep(1.0)
        return "never"

    class SlowPlugin(Plugin):
        name = "slow"
        description = "slow plugin"

        def get_tools(self) -> list[Tool]:
            return [
                Tool(
                    name="slow_tool",
                    description="hangs",
                    input_schema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                    handler=_slow,
                )
            ]

    registry.register(SlowPlugin())

    result = asyncio.run(registry.execute_tool_async("slow_tool", {}))
    assert result.is_error
    assert "timed out" in str(result.content)


def test_tool_use_id_generated_when_provider_omits_one():
    """Future-proofing: providers that don't emit IDs (Ollama) get one anyway."""
    registry = PluginRegistry()
    registry.register(_AddPlugin())

    provider = _ScriptedProvider([
        [
            AgentChunk(
                type="tool_use",
                tool_name="add",
                tool_args={"a": 1, "b": 1},
                # No tool_use_id given
            ),
            AgentChunk(type="done"),
        ],
        [
            AgentChunk(type="text_delta", text="2"),
            AgentChunk(type="done"),
        ],
    ])
    core = AgentCore(provider, tool_executor=registry.execute_tool_async)
    chunks = _collect(core.run("hi"))
    tool_use = next(c for c in chunks if c.type == "tool_use")
    assert tool_use.tool_use_id  # AgentCore must have synthesized one


@pytest.mark.parametrize(
    "args, ok",
    [
        ({"a": 1, "b": 2}, True),
        ({"a": "x", "b": 2}, False),  # wrong type
        ({"a": 1}, False),  # missing required
        ({"a": 1, "b": 2, "c": 3}, False),  # additionalProperties=False
    ],
)
def test_basic_validation(args, ok):
    registry = PluginRegistry()
    registry.register(_AddPlugin())
    result = asyncio.run(registry.execute_tool_async("add", args))
    assert (not result.is_error) is ok
