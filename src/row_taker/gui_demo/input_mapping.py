from __future__ import annotations

import pygame

from row_taker.client.state import ClientState
from row_taker.gui_demo.screens.game_screen import GameScreenTargets, handle_game_event
from row_taker.gui_demo.screens.lobby_screen import LobbyScreenTargets, handle_lobby_event
from row_taker.gui_demo.ui.screen_result import ScreenResult


GuiDemoInput = ScreenResult
NO_INPUT = ScreenResult()


def map_pygame_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    interaction_map: LobbyScreenTargets | GameScreenTargets | None,
) -> ScreenResult:
    if state is not None and state.client_mode.value == 'lobby':
        lobby_targets = interaction_map if isinstance(interaction_map, LobbyScreenTargets) else None
        return handle_lobby_event(event, state=state, lobby_targets=lobby_targets)

    game_targets = interaction_map if isinstance(interaction_map, GameScreenTargets) else None
    return handle_game_event(event, state=state, game_targets=game_targets)
