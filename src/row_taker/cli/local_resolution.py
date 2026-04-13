from __future__ import annotations

from dataclasses import dataclass

from row_taker.cli.row_display import format_resolution_steps_for_cli
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PublicPlayerInfo, Row
from row_taker.engine.game.phases import StepAction
from row_taker.engine.game.public_state_ops import apply_resolution_step
from row_taker.engine.game.rules import place_card, take_row, target_row_index
from row_taker.engine.game.state import PublicState, TrickResolutionStep
from row_taker.protocol.messages import CardsRevealed, PlayedCardView


@dataclass(frozen=True, slots=True)
class LocalResolutionState:
    shadow_state: PublicState
    remaining_plays: tuple[PlayedCardView, ...]
    pending_row_choice: PlayedCardView | None
    steps: tuple[TrickResolutionStep, ...]
    lines: tuple[str, ...]


def start_local_resolution(public_state: PublicState, revealed: CardsRevealed) -> LocalResolutionState:
    ordered = tuple(sorted(revealed.plays, key=lambda play: play.card_value))
    initial = LocalResolutionState(
        shadow_state=_clone_public_state(public_state),
        remaining_plays=ordered,
        pending_row_choice=None,
        steps=(),
        lines=(),
    )
    return _advance_until_blocked(initial)


def apply_local_row_choice(state: LocalResolutionState, row_id) -> LocalResolutionState:
    play = state.pending_row_choice
    if play is None:
        return state

    current_state = state.shadow_state
    chosen_index = current_state.get_row_index(row_id)
    previous_cards = tuple(current_state.rows[chosen_index].cards)

    rows = [Row(row_id=row.row_id, cards=list(row.cards)) for row in current_state.rows]
    bullheads, _taken = take_row(rows, chosen_index)
    rows[chosen_index].cards = [Card(play.card_value)]

    step = TrickResolutionStep(
        action=StepAction.TOOK_ROW_SMALL,
        player_id=play.player_id,
        affected_row_id=row_id,
        played_card=Card(play.card_value),
        taken_cards=tuple(previous_cards),
        points_gained=bullheads,
        new_row_cards=tuple(rows[chosen_index].cards),
    )
    next_shadow_state = apply_resolution_step(current_state, step)
    step_line = format_resolution_steps_for_cli(current_state, [step])[0]

    resumed = LocalResolutionState(
        shadow_state=next_shadow_state,
        remaining_plays=state.remaining_plays,
        pending_row_choice=None,
        steps=state.steps + (step,),
        lines=state.lines + (step_line,),
    )
    return _advance_until_blocked(resumed)


def _advance_until_blocked(state: LocalResolutionState) -> LocalResolutionState:
    current = state
    while current.pending_row_choice is None and current.remaining_plays:
        play = current.remaining_plays[0]
        card = Card(play.card_value)
        row_index = target_row_index(current.shadow_state.rows, card)

        if row_index is None:
            return LocalResolutionState(
                shadow_state=current.shadow_state,
                remaining_plays=current.remaining_plays[1:],
                pending_row_choice=play,
                steps=current.steps,
                lines=current.lines + (f"- {play.player_name} muss mit {card.value} eine Reihe wählen.",),
            )

        row = current.shadow_state.rows[row_index]
        previous_cards = tuple(row.cards)
        rows = [Row(row_id=existing.row_id, cards=list(existing.cards)) for existing in current.shadow_state.rows]
        bullheads, taken = place_card(rows, row_index, card, row_capacity=current.shadow_state.config.row_capacity)
        next_row_cards = tuple(rows[row_index].cards)
        step = TrickResolutionStep(
            action=StepAction.PLACED if taken is None else StepAction.TOOK_ROW_OVERFLOW,
            player_id=play.player_id,
            affected_row_id=row.row_id,
            played_card=card,
            taken_cards=tuple(previous_cards) if taken is not None else (),
            points_gained=bullheads if taken is not None else 0,
            new_row_cards=next_row_cards,
        )
        next_shadow_state = apply_resolution_step(current.shadow_state, step)
        step_line = format_resolution_steps_for_cli(current.shadow_state, [step])[0]
        current = LocalResolutionState(
            shadow_state=next_shadow_state,
            remaining_plays=current.remaining_plays[1:],
            pending_row_choice=None,
            steps=current.steps + (step,),
            lines=current.lines + (step_line,),
        )
    return current


def _clone_public_state(public_state: PublicState) -> PublicState:
    return PublicState(
        config=public_state.config,
        players=[
            PublicPlayerInfo(
                player_id=player.player_id,
                name=player.name,
                score=player.score,
                hand_count=player.hand_count,
            )
            for player in public_state.players
        ],
        rows=[Row(row_id=row.row_id, cards=list(row.cards)) for row in public_state.rows],
        round_no=public_state.round_no,
        trick_no=public_state.trick_no,
        phase_info=public_state.phase_info,
    )
