from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.presentation_builder import (
    build_presentation_card_placed,
    build_presentation_cards_revealed,
    build_presentation_overflow_resolved,
    build_presentation_row_choice_required,
    build_presentation_row_chosen,
    build_presentation_row_taken,
    build_presentation_trick_finished,
)
from row_taker.client.presentation_events import PresentationEvent
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import EngineRow, PublicPlayerInfo, Row
from row_taker.engine.game.phases import StepAction
from row_taker.engine.game.public_state_ops import apply_resolution_step
from row_taker.engine.game.rules import place_card, take_row, target_row_index
from row_taker.engine.game.state import PublicState, TrickResolutionStep
from row_taker.protocol.messages import CardsRevealed, PlayedCardView


@dataclass(frozen=True, slots=True)
class TrickPresentationState:
    shadow_state: PublicState
    remaining_plays: tuple[PlayedCardView, ...]
    pending_row_choice: PlayedCardView | None
    steps: tuple[TrickResolutionStep, ...]
    events: tuple[PresentationEvent, ...]


def start_trick_presentation(public_state: PublicState, revealed: CardsRevealed) -> TrickPresentationState:
    ordered = tuple(sorted(revealed.plays, key=lambda play: play.card_value))
    initial = TrickPresentationState(
        shadow_state=_clone_public_state(public_state),
        remaining_plays=ordered,
        pending_row_choice=None,
        steps=(),
        events=(build_presentation_cards_revealed(revealed.plays),),
    )
    return _advance_until_blocked(initial)


def apply_trick_row_choice(state: TrickPresentationState, row_id: int) -> TrickPresentationState:
    play = state.pending_row_choice
    if play is None:
        return state

    current_state = state.shadow_state
    chosen_index = current_state.get_row_index(row_id)
    previous_cards = tuple(current_state.rows[chosen_index].cards)

    rows = [EngineRow(row_id=row.row_id, cards=list(row.cards)) for row in current_state.rows]
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
    player_names = _player_names_for_state(current_state)

    resumed = TrickPresentationState(
        shadow_state=next_shadow_state,
        remaining_plays=state.remaining_plays,
        pending_row_choice=None,
        steps=state.steps + (step,),
        events=state.events
        + (
            build_presentation_row_chosen(
                player_id=play.player_id,
                player_names=player_names,
                row_id=row_id,
                card_value=play.card_value,
            ),
            build_presentation_row_taken(
                player_id=play.player_id,
                player_names=player_names,
                row_id=row_id,
                taken_cards=tuple(card.value for card in previous_cards),
                bullheads=bullheads,
                replacement_card_value=play.card_value,
                row_cards_after=tuple(card.value for card in rows[chosen_index].cards),
            ),
        ),
    )
    return _advance_until_blocked(resumed)


def _advance_until_blocked(state: TrickPresentationState) -> TrickPresentationState:
    current = state
    while current.pending_row_choice is None and current.remaining_plays:
        play = current.remaining_plays[0]
        card = Card(play.card_value)
        row_index = target_row_index(current.shadow_state.rows, card)
        player_names = _player_names_for_state(current.shadow_state)

        if row_index is None:
            return TrickPresentationState(
                shadow_state=current.shadow_state,
                remaining_plays=current.remaining_plays[1:],
                pending_row_choice=play,
                steps=current.steps,
                events=current.events
                + (
                    build_presentation_row_choice_required(
                        player_id=play.player_id,
                        player_names=player_names,
                        card_value=card.value,
                    ),
                ),
            )

        row = current.shadow_state.rows[row_index]
        previous_cards = tuple(row.cards)
        rows = [EngineRow(row_id=existing.row_id, cards=list(existing.cards)) for existing in current.shadow_state.rows]
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
        if taken is None:
            next_event: PresentationEvent = build_presentation_card_placed(
                player_id=play.player_id,
                player_names=player_names,
                card_value=card.value,
                row_id=row.row_id,
                row_cards_after=tuple(item.value for item in next_row_cards),
            )
        else:
            next_event = build_presentation_overflow_resolved(
                player_id=play.player_id,
                player_names=player_names,
                row_id=row.row_id,
                card_value=card.value,
                taken_cards=tuple(item.value for item in previous_cards),
                bullheads=bullheads,
                row_cards_after=tuple(item.value for item in next_row_cards),
            )
        current = TrickPresentationState(
            shadow_state=next_shadow_state,
            remaining_plays=current.remaining_plays[1:],
            pending_row_choice=None,
            steps=current.steps + (step,),
            events=current.events + (next_event,),
        )
    if current.pending_row_choice is None and not current.remaining_plays:
        return TrickPresentationState(
            shadow_state=current.shadow_state,
            remaining_plays=current.remaining_plays,
            pending_row_choice=None,
            steps=current.steps,
            events=current.events + (build_presentation_trick_finished(),),
        )
    return current


def _clone_public_state(public_state: PublicState) -> PublicState:
    return PublicState(
        config=public_state.config,
        players=tuple(
            PublicPlayerInfo(
                player_id=player.player_id,
                name=player.name,
                score=player.score,
                hand_count=player.hand_count,
            )
            for player in public_state.players
        ),
        rows=tuple(Row(row_id=row.row_id, cards=tuple(row.cards)) for row in public_state.rows),
        round_no=public_state.round_no,
        trick_no=public_state.trick_no,
        phase_info=public_state.phase_info,
    )


def _player_names_for_state(public_state: PublicState) -> dict[str, str]:
    return {player.player_id: player.name for player in public_state.players}
