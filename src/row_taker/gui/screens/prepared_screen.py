from __future__ import annotations

from typing import Protocol

import pygame

from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.screen_result import ScreenResult


class PreparedScreen(Protocol):
    """A production screen prepared with all geometry and interaction targets."""

    def handle_event(self, event: pygame.event.Event) -> ScreenResult: ...

    def render(
        self,
        surface: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
    ) -> None: ...
