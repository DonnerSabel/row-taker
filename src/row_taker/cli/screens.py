from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from row_taker.client.core_state import ClientMode, PendingAction
from row_taker.client.state import ClientState
from row_taker.engine.game.state import PlayerState


@dataclass(frozen=True, slots=True)
class LobbyScreen:
    kind: Literal["main", "rename", "seat_edit", "bot_name"]
    seat_index: int | None = None


@dataclass(frozen=True, slots=True)
class GameScreen:
    kind: Literal["waiting", "choose_card", "choose_row", "ended"]
    player_state: PlayerState | None = None


Screen = LobbyScreen | GameScreen



def current_screen(state: ClientState) -> Screen:
    if state.client_mode == ClientMode.LOBBY:
        return LobbyScreen(
            kind=state.navigation_state.lobby_submenu,
            seat_index=state.navigation_state.selected_seat_index,
        )
    if state.client_mode == ClientMode.ENDED:
        return GameScreen(kind="ended", player_state=state.player_state)
    if state.pending_action == PendingAction.CHOOSE_CARD:
        return GameScreen(kind="choose_card", player_state=state.player_state)
    if state.pending_action == PendingAction.CHOOSE_ROW:
        return GameScreen(kind="choose_row", player_state=state.player_state)
    return GameScreen(kind="waiting", player_state=state.player_state)
