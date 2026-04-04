from .models import PlayerID, PublicPlayerInfo, Row
from .state import GameState, PlayerState


def build_player_state(game_state: GameState, self_player_id: PlayerID) -> PlayerState:
    self_player = game_state.get_player_by_id(self_player_id)

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

    visible_hand = list(self_player.hand)

    return PlayerState(
        config=game_state.config,
        self_player_id=self_player_id,
        players=public_players,
        rows=visible_rows,
        hand=visible_hand,
        round_no=game_state.round_no,
        trick_no=game_state.trick_no,
        phase_info=game_state.phase_info,
    )
