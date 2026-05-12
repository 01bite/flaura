# flaura

An agentic terminal — a full-screen TUI that lets you talk to a local LLM, extend it with plugins, and control everything from the keyboard.

## Features

- **Streaming agent** — responses stream token-by-token directly into the output pane
- **Ollama provider** — runs fully offline; connects to any model you have pulled locally; no API key required
- **Plugin system** — extend the agent with tools; scaffold new plugins with one command
- **Command overlay** — vim-style `:command` mode for switching providers, managing plugins, and more
- **Normal / Multi input modes** — Esc toggles between single-line (Enter = submit) and multi-line (Enter = newline) input
- **Live model discovery** — `:provider ollama <Tab>` lists models currently available in your Ollama install
- **Persistent history** — full conversation history saved to `~/.flaura/history.txt` (mode `0600`)
- **TOML config** — written on first run to `~/.flaura/config.toml`; every option is commented and explained

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/download) installed and running locally

## Install

```sh
git clone <repo>
cd flaura
pip install -e ".[ollama]"
```

Pull a model if you haven't already:

```sh
ollama pull llama3-groq-tool-use:8 
```

## Run

```sh
flaura
```

### Debug mode

```sh
flaura --debug
```

Enables direct tool invocation for testing plugins without going through the LLM. A red `[DEBUG]` indicator appears in the status bar, and a new command is available:

```
:tool <tool_name> <json-args>
```

Examples:

```
:tool mytools_hello {"name": "world"}
:tool mytools_add {"a": 1, "b": 2}
:tool somethingnoarg {}
```

Tab-completion lists every registered tool name. Output is appended inline as `[tool: <name>] <result>` (or `[tool_error: <name>] …` on failure). Args are validated against the tool's `input_schema` just like agent-driven calls.

## Key bindings

| Key | Action |
|-----|--------|
| `Enter` | Submit (Normal mode) / New line (Multi mode) |
| `Esc` | Toggle Normal ↔ Multi input mode |
| `:` | Open command overlay |
| `Ctrl-C` | Cancel in-progress agent response |
| `Ctrl-D` | Quit |
| `Tab` | Autocomplete commands and model names |
| `↑ / ↓` | Navigate history |
| `Ctrl-R` | Search history |

## Commands

| Command | Description |
|---------|-------------|
| `:provider ollama [model]` | Switch to Ollama; optionally specify a model |
| `:provider echo` | Switch to the built-in echo provider (no LLM) |
| `:plugins` | List loaded plugins |
| `:tools` | List available tools |
| `:plugin create <name>` | Scaffold a new plugin in `~/.flaura/plugins/<name>/` |
| `:plugin remove <name>` | Unload a plugin for this session |
| `:quit` | Exit flaura |

## Configuration

On first run flaura writes `~/.flaura/config.toml`:

```toml
[app]
provider = "echo"

[providers.ollama]
# model = ""   # leave blank to auto-select first available model
host = "http://localhost:11434"

[ui.colors]
# override any style token here
```

To start with Ollama by default, set `provider = "ollama"` under `[app]`.

## Plugins

Plugins are Python packages that expose tools the agent can call. Each plugin lives in its own directory under `~/.flaura/plugins/`.

### Create a plugin

```
:plugin create mytools
```

This generates:

```
~/.flaura/plugins/mytools/
    plugin.toml     # metadata + entry point
    plugin.py       # Plugin subclass with two example tools
```

Open `plugin.py`, replace the dummy `_hello` and `_add` functions with your own, and restart flaura. The agent will automatically see and use your tools.

### Plugin structure

```python
from flaura.plugins.base import Plugin
from flaura.plugins.types import Tool

class MyPlugin(Plugin):
    name = "mytools"
    description = "my custom tools"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="mytools_fetch",
                description="Fetch the contents of a URL.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                    },
                    "required": ["url"],
                    "additionalProperties": False,
                },
                handler=my_fetch_function,
            ),
        ]
```

Third-party plugins can also be distributed as Python packages and registered via the `flaura.plugins` entry-point group.

## Development

```sh
pip install -e ".[dev,ollama]"
pytest
ruff check src/
```

## License

GNU GENERAL PUBLIC LICENSE V3
