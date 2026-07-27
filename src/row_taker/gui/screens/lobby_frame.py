from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.state import ClientState
from row_taker.gui.layout import GuiLayout
from row_taker.gui.lobby_interaction import (
    LobbyScreenTargets,
    build_lobby_screen_targets,
    handle_lobby_event,
)
from row_taker.gui.lobby_renderer import render_lobby_screen
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.screen_result import ScreenResult


@dataclass(frozen=True, slots=True)
class LobbyFrame:
    """One fully prepared production frame of the lobby screen."""

    state: ClientState
    layout: GuiLayout
    targets: LobbyScreenTargets
    mouse_pos: tuple[int, int] = (-1, -1)

    @classmethod
    def from_layout(
        cls,
        *,
        layout: GuiLayout,
        state: ClientState,
        mouse_pos: tuple[int, int] | None = None,
    ) -> LobbyFrame:
        return cls(
            state=state,
            layout=layout,
            targets=build_lobby_screen_targets(layout, state),
            mouse_pos=_current_mouse_pos() if mouse_pos is None else mouse_pos,
        )

    def handle_event(self, event: pygame.event.Event) -> ScreenResult:
        return handle_lobby_event(
            event,
            state=self.state,
            lobby_targets=self.targets,
        )

    def render(
        self,
        screen: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
    ) -> None:
        render_lobby_screen(
            screen,
            drawer=drawer,
            layout=self.layout,
            client_state=self.state,
            lobby_targets=self.targets,
            mouse_pos=self.mouse_pos,
        )


def _current_mouse_pos() -> tuple[int, int]:
    try:
        return pygame.mouse.get_pos()
    except pygame.error:
        return (-1, -1)


__all__ = ["LobbyFrame"]
