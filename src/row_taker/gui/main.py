"""Graphical Row-Taker client entry point."""

from __future__ import annotations

from row_taker.gui.app import GuiApp
from row_taker.logging_utils import configure_logging


def run() -> int:
    """Run the graphical client and return a process exit code."""
    configure_logging()
    try:
        return GuiApp().run()
    except KeyboardInterrupt:
        return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
