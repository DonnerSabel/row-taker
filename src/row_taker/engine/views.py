from __future__ import annotations

from row_taker.engine.models import PlayerID, PublicPlayerInfo, Row
from row_taker.engine.state import GameState, PlayerState, PublicState


def build_public_state(game_state: GameState) -> PublicState:
    public_players = [
        PublicPlayerInfo(
            player_id=player.player_id,
            name=player.name,
            score=player.score,
            hand_count=len(player.hand),
        )
        for player in game_state.players
    ]

    visible_rows = [
        Row(row_id=row.row_id, cards=list(row.cards))
        for row in game_state.rows
    ]

    return PublicState(
        config=game_state.config,
        players=public_players,
        rows=visible_rows,
        round_no=game_state.round_no,
        trick_no=game_state.trick_no,
        phase_info=game_state.phase_info,
    )


def build_player_state(game_state: GameState, self_player_id: PlayerID) -> PlayerState:
    self_player = game_state.get_player_by_id(self_player_id)

    return PlayerState(
        public_state=build_public_state(game_state),
        self_player_id=self_player_id,
        hand=list(self_player.hand),
    )
