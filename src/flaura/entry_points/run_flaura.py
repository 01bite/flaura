from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="flaura", description="Agentic terminal UI")
    parser.add_argument(
        "--app-home",
        metavar="DIR",
        help="App home directory (default: ~/.flaura, or $FLAURA_HOME)",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Config file path (default: <app-home>/config.toml)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug commands (e.g. :tool <name> <json-args> for direct invocation)",
    )
    args = parser.parse_args()

    from flaura.config import FlauraConfig
    from flaura.core.app import FlauraApp

    config = FlauraConfig.load(
        app_home=Path(args.app_home).expanduser() if args.app_home else None,
        config_file=Path(args.config).expanduser() if args.config else None,
    )

    FlauraApp(config=config, debug=args.debug).run()


def run() -> None:
    main()
