from __future__ import annotations

from row_taker.engine.cards import Card
from row_taker.engine.models import PlayerID, PublicPlayerInfo, Row
from row_taker.engine.state import DeltaPublicState, GameState, PlayerState, PublicState, get_player_index, get_row_index


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


def _score_delta_from_public_transition(old_row: Row, delta: DeltaPublicState) -> int:
    expected_appended_cards = list(old_row.cards) + [delta.played_card]
    if [card.value for card in delta.new_row_cards] == [card.value for card in expected_appended_cards]:
        return 0
    return old_row.bullheads()


def apply_delta_public_state(public_state: PublicState, delta: DeltaPublicState) -> PublicState:
    players = list(public_state.players)
    rows = [Row(row_id=row.row_id, cards=list(row.cards)) for row in public_state.rows]

    player_index = get_player_index(players, delta.player_id)
    row_index = get_row_index(rows, delta.affected_row_id)

    old_row = rows[row_index]
    score_delta = _score_delta_from_public_transition(old_row, delta)

    rows[row_index] = Row(
        row_id=old_row.row_id,
        cards=list(delta.new_row_cards),
    )

    old_player = players[player_index]
    players[player_index] = PublicPlayerInfo(
        player_id=old_player.player_id,
        name=old_player.name,
        score=old_player.score + score_delta,
        hand_count=old_player.hand_count - 1,
    )

    return PublicState(
        config=public_state.config,
        players=players,
        rows=rows,
        round_no=public_state.round_no,
        trick_no=public_state.trick_no,
        phase_info=public_state.phase_info,
    )


def apply_deltas_public_state(
    public_state: PublicState,
    deltas: list[DeltaPublicState],
) -> PublicState:
    current_state = public_state
    for delta in deltas:
        current_state = apply_delta_public_state(current_state, delta)
    return current_state


def score_delta_for_public_delta(public_state: PublicState, delta: DeltaPublicState) -> int:
    row_index = get_row_index(public_state.rows, delta.affected_row_id)
    return _score_delta_from_public_transition(public_state.rows[row_index], delta)


def is_row_take_public_delta(public_state: PublicState, delta: DeltaPublicState) -> bool:
    row_index = get_row_index(public_state.rows, delta.affected_row_id)
    old_row = public_state.rows[row_index]
    expected_appended_cards = list(old_row.cards) + [delta.played_card]
    return [card.value for card in delta.new_row_cards] != [card.value for card in expected_appended_cards]


def classify_row_take_public_delta(public_state: PublicState, delta: DeltaPublicState) -> str:
    row_index = get_row_index(public_state.rows, delta.affected_row_id)
    old_row = public_state.rows[row_index]
    if not is_row_take_public_delta(public_state, delta):
        return 'placed'
    if delta.played_card.value < old_row.last_value():
        return 'took_row_small'
    return 'took_row_overflow'
