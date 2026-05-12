from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any

from flaura.plugins.base import Plugin
from flaura.plugins.types import Tool, ToolResult

if TYPE_CHECKING:
    from flaura.agent.types import ProviderToolSchema


DEFAULT_TOOL_TIMEOUT_S = 30.0


class PluginRegistry:
    """Holds all registered plugins and a flat tool index for the agent."""

    def __init__(self, tool_timeout_s: float = DEFAULT_TOOL_TIMEOUT_S) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._tools: dict[str, Tool] = {}
        self._tool_timeout_s = tool_timeout_s

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"plugin {plugin.name!r} is already registered")
        for tool in plugin.get_tools():
            if tool.name in self._tools:
                owner = self._tools[tool.name].plugin_name
                raise ValueError(
                    f"tool {tool.name!r} from plugin {plugin.name!r} "
                    f"conflicts with the same-named tool from {owner!r}"
                )
        self._plugins[plugin.name] = plugin
        for tool in plugin.get_tools():
            tool.plugin_name = plugin.name
            self._tools[tool.name] = tool

    def unregister(self, plugin_name: str) -> None:
        if plugin_name not in self._plugins:
            return
        plugin = self._plugins.pop(plugin_name)
        for tool in plugin.get_tools():
            self._tools.pop(tool.name, None)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_tool_schemas(self) -> list[ProviderToolSchema]:
        """Provider-neutral schemas for the agent."""
        from flaura.agent.types import ProviderToolSchema
        return [
            ProviderToolSchema(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in self._tools.values()
        ]

    def execute_tool(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Synchronous tool invocation. Used by the debug `:tool` command."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(content=f"unknown tool: {name}", is_error=True)

        validation_error = validate_args(args, tool.input_schema)
        if validation_error:
            return ToolResult(
                content=f"invalid arguments for {name}: {validation_error}",
                is_error=True,
            )

        try:
            result = tool.handler(**args)
            if inspect.isawaitable(result):
                # The caller is synchronous; we cannot await here. Surface a clear error
                # rather than returning the coroutine object.
                return ToolResult(
                    content=(
                        f"tool {name!r} is async; invoke it through the agent "
                        f"or call execute_tool_async()"
                    ),
                    is_error=True,
                )
            return ToolResult(content=result, is_error=False)
        except Exception as e:
            return ToolResult(content=f"{type(e).__name__}: {e}", is_error=True)

    async def execute_tool_async(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Async tool invocation with a timeout. Used by the agent loop."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(content=f"unknown tool: {name}", is_error=True)

        validation_error = validate_args(args, tool.input_schema)
        if validation_error:
            return ToolResult(
                content=f"invalid arguments for {name}: {validation_error}",
                is_error=True,
            )

        try:
            coro = _invoke(tool, args)
            result = await asyncio.wait_for(coro, timeout=self._tool_timeout_s)
            return ToolResult(content=result, is_error=False)
        except TimeoutError:
            return ToolResult(
                content=f"tool {name!r} timed out after {self._tool_timeout_s}s",
                is_error=True,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return ToolResult(content=f"{type(e).__name__}: {e}", is_error=True)


async def _invoke(tool: Tool, args: dict[str, Any]) -> Any:
    """Call a tool's handler, awaiting it if it's async, threading it if sync."""
    if inspect.iscoroutinefunction(tool.handler):
        return await tool.handler(**args)
    return await asyncio.to_thread(tool.handler, **args)


# ── JSON-Schema validation ───────────────────────────────────────────────────


def validate_args(args: Any, schema: dict[str, Any]) -> str | None:
    """Validate `args` against a JSON Schema. Returns an error string or None.

    Uses the `jsonschema` library which supports `$ref`, `oneOf`/`anyOf`/`allOf`,
    `enum`, `pattern`, nested objects, numeric bounds, length bounds, and the
    full Draft 2020-12 spec. The validator is cached per schema id so repeated
    tool calls don't pay the compile cost.
    """
    if not isinstance(schema, dict):
        return None

    try:
        import jsonschema
    except ImportError:
        return _fallback_validate(args, schema)

    validator = _get_validator(jsonschema, schema)
    errors = sorted(validator.iter_errors(args), key=lambda e: e.path)
    if not errors:
        return None
    first = errors[0]
    path = "/".join(str(p) for p in first.absolute_path) or "<root>"
    return f"{path}: {first.message}"


_validator_cache: dict[int, Any] = {}


def _get_validator(jsonschema_mod: Any, schema: dict[str, Any]) -> Any:
    key = id(schema)
    cached = _validator_cache.get(key)
    if cached is not None:
        return cached
    cls = jsonschema_mod.validators.validator_for(schema)
    cls.check_schema(schema)
    validator = cls(schema)
    _validator_cache[key] = validator
    return validator


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


def _fallback_validate(args: Any, schema: dict[str, Any]) -> str | None:
    """Minimal validator used when the `jsonschema` package is unavailable.

    Covers `type`, `required`, `additionalProperties: false`. Anything more
    complex (`$ref`, `oneOf`, `enum`, `pattern`, nested objects) passes silently.
    Install `jsonschema` for full coverage.
    """
    if not isinstance(args, dict):
        return f"expected object, got {type(args).__name__}"

    properties = schema.get("properties") or {}
    required = schema.get("required") or []

    for key in required:
        if key not in args:
            return f"missing required field {key!r}"

    if schema.get("additionalProperties") is False:
        for key in args:
            if key not in properties:
                return f"unexpected field {key!r}"

    for key, value in args.items():
        prop_schema = properties.get(key)
        if not isinstance(prop_schema, dict):
            continue
        expected = prop_schema.get("type")
        if expected is None:
            continue
        types = expected if isinstance(expected, list) else [expected]
        allowed: tuple[type, ...] = tuple(t for typ in types for t in _JSON_TYPES.get(typ, ()))
        if not allowed:
            continue
        if isinstance(value, bool) and bool not in allowed:
            return f"field {key!r} expected {expected}, got bool"
        if not isinstance(value, allowed):
            return f"field {key!r} expected {expected}, got {type(value).__name__}"
    return None
