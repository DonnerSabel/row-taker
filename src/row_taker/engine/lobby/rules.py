from __future__ import annotations

from row_taker.engine.lobby.state import LobbyState


def validate_lobby_state(lobby_state: LobbyState) -> None:
    if lobby_state.match_config is not None:
        lobby_state.match_config.validate()


def can_start_game(lobby_state: LobbyState) -> bool:
    validate_lobby_state(lobby_state)
    return lobby_state.match_config is not None and not lobby_state.game_started
