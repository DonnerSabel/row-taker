"""Modern graphical Row-Taker client.

This entrypoint intentionally uses the same architecture as ``row_taker.gui_demo``:
GUI -> LiveGuiClient -> GameClientCore -> protocol/transport.

The visual client can grow its own screens and rendering step by step, but it must not
reintroduce the old CLI state machine.
"""

from __future__ import annotations

from row_taker.gui_demo.app import GuiDemoApp
from row_taker.logging_utils import configure_logging


def run() -> int:
    """Run the graphical client and return a process exit code."""
    configure_logging()
    try:
        return GuiDemoApp().run()
    except KeyboardInterrupt:
        return 0


# Backwards-compatible name for older scripts such as run_lobby_gui.py.
def run_lobby() -> int:
    return run()


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
