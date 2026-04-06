from __future__ import annotations

from row_taker.engine.models import PublicPlayerInfo, Row
from row_taker.engine.phases import StepAction
from row_taker.engine.state import DeltaPublicState, PublicState, get_player_index, get_row_index


def played_card_from_delta(delta: DeltaPublicState):
    return delta.played_card()


def _is_append_transition(old_row: Row, delta: DeltaPublicState) -> bool:
    expected_appended_cards = tuple(old_row.cards) + (played_card_from_delta(delta),)
    return delta.new_row_cards == expected_appended_cards


def score_delta_for_public_delta(public_state: PublicState, delta: DeltaPublicState) -> int:
    row_index = get_row_index(public_state.rows, delta.affected_row_id)
    old_row = public_state.rows[row_index]
    if _is_append_transition(old_row, delta):
        return 0
    return old_row.bullheads()


def classify_public_delta(public_state: PublicState, delta: DeltaPublicState) -> StepAction:
    row_index = get_row_index(public_state.rows, delta.affected_row_id)
    old_row = public_state.rows[row_index]
    if _is_append_transition(old_row, delta):
        return StepAction.PLACED
    if played_card_from_delta(delta).value < old_row.last_value():
        return StepAction.TOOK_ROW_SMALL
    return StepAction.TOOK_ROW_OVERFLOW


def apply_delta_public_state(public_state: PublicState, delta: DeltaPublicState) -> PublicState:
    players = list(public_state.players)
    rows = [Row(row_id=row.row_id, cards=list(row.cards)) for row in public_state.rows]

    player_index = get_player_index(players, delta.player_id)
    row_index = get_row_index(rows, delta.affected_row_id)
    score_delta = score_delta_for_public_delta(public_state, delta)

    old_row = rows[row_index]
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


def apply_deltas_public_state(public_state: PublicState, deltas: tuple[DeltaPublicState, ...] | list[DeltaPublicState]) -> PublicState:
    current_state = public_state
    for delta in deltas:
        current_state = apply_delta_public_state(current_state, delta)
    return current_state
