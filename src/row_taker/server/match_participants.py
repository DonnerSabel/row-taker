from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.models import PlayerID
from row_taker.engine.lobby.state import LobbyState, ordered_seated_client_ids


@dataclass(frozen=True, slots=True)
class MatchParticipants:
    ordered_client_ids: tuple[str, ...]
    player_to_client_id: dict[PlayerID, str]
    client_to_player_id: dict[str, PlayerID]


def build_match_participants(lobby_state: LobbyState) -> MatchParticipants:
    ordered_client_ids = ordered_seated_client_ids(lobby_state)
    player_to_client_id = {
        PlayerID(f'player-{index}'): client_id
        for index, client_id in enumerate(ordered_client_ids)
    }
    client_to_player_id = {
        client_id: player_id
        for player_id, client_id in player_to_client_id.items()
    }
    return MatchParticipants(
        ordered_client_ids=ordered_client_ids,
        player_to_client_id=player_to_client_id,
        client_to_player_id=client_to_player_id,
    )
