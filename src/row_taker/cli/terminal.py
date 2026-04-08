from __future__ import annotations

import os
import sys


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != "nt" and not os.environ.get("TERM"):
        return
    os.system("cls" if os.name == "nt" else "clear")
