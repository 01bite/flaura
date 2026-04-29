from __future__ import annotations

import argparse

from flaura.core.app import FlauraApp


def main() -> None:
    parser = argparse.ArgumentParser(prog="flaura", description="terminal ui")
    parser.parse_args()

    FlauraApp().run()


def run() -> None:
    main()
