from __future__ import annotations

from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PublicPlayerInfo, Row
from row_taker.engine.game.state import PublicState, TrickResolutionStep, get_player_index, get_row_index


def played_card_from_step(step: TrickResolutionStep) -> Card:
    return step.played_card


def apply_resolution_step(public_state: PublicState, step: TrickResolutionStep) -> PublicState:
    players = list(public_state.players)
    rows = [Row(row_id=row.row_id, cards=tuple(row.cards)) for row in public_state.rows]

    player_index = get_player_index(players, step.player_id)
    row_index = get_row_index(rows, step.affected_row_id)

    old_row = rows[row_index]
    rows[row_index] = Row(
        row_id=old_row.row_id,
        cards=tuple(step.new_row_cards),
    )

    old_player = players[player_index]
    players[player_index] = PublicPlayerInfo(
        player_id=old_player.player_id,
        name=old_player.name,
        score=old_player.score + step.points_gained,
        hand_count=old_player.hand_count - 1,
    )

    return PublicState(
        config=public_state.config,
        players=tuple(players),
        rows=tuple(rows),
        round_no=public_state.round_no,
        trick_no=public_state.trick_no,
        phase_info=public_state.phase_info,
    )


def apply_resolution_steps(
    public_state: PublicState,
    steps: tuple[TrickResolutionStep, ...] | list[TrickResolutionStep],
) -> PublicState:
    current_state = public_state
    for step in steps:
        current_state = apply_resolution_step(current_state, step)
    return current_state
