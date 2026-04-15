from __future__ import annotations

from row_taker.gui_demo.app import GuiDemoApp
from row_taker.logging_utils import configure_logging


def main() -> None:
    configure_logging()
    GuiDemoApp().run()


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        return 0
