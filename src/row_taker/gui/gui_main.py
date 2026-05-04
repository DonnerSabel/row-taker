"""Modern graphical Row-Taker client."""

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


# Backwards-compatible name for older scripts such as run_lobby_gui.py.
def run_lobby() -> int:
    return run()


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
