from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from row_taker.gui.app import GuiApp

__all__ = ["GuiApp"]


def __getattr__(name: str) -> Any:
    if name == "GuiApp":
        from row_taker.gui.app import GuiApp

        return GuiApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
