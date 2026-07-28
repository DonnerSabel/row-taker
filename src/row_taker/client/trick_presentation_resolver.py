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
from row_taker.client.presentation_steps import PresentationStep
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.phases import StepAction
from row_taker.engine.game.public_state_ops import apply_resolution_step
from row_taker.engine.game.rules import place_card, take_row, target_row_index
from row_taker.engine.game.state import EnginePublicState, PublicState, TrickResolutionStep
from row_taker.protocol.messages import CardsRevealed, PlayedCardView


@dataclass(frozen=True, slots=True)
class TrickPresentationState:
    shadow_state: PublicState
    remaining_plays: tuple[PlayedCardView, ...]
    pending_row_choice: PlayedCardView | None
    resolution_steps: tuple[TrickResolutionStep, ...]
    presentation_steps: tuple[PresentationStep, ...]


def start_trick_presentation(
    public_state: PublicState, revealed: CardsRevealed
) -> TrickPresentationState:
    ordered = tuple(sorted(revealed.plays, key=lambda play: play.card_value))
    initial_shadow_state = _clone_public_state(public_state)
    revealed_event = build_presentation_cards_revealed(revealed.plays)
    initial = TrickPresentationState(
        shadow_state=initial_shadow_state,
        remaining_plays=ordered,
        pending_row_choice=None,
        resolution_steps=(),
        presentation_steps=(_unchanged_presentation_step(revealed_event, initial_shadow_state),),
    )
    return _advance_until_blocked(initial)


def apply_trick_row_choice(state: TrickPresentationState, row_id: RowID) -> TrickPresentationState:
    play = state.pending_row_choice
    if play is None:
        return state

    current_state = state.shadow_state
    chosen_index = current_state.get_row_index(row_id)
    previous_cards = tuple(current_state.rows[chosen_index].cards)

    engine_state = EnginePublicState.from_public_state(current_state)
    bullheads, _taken = take_row(engine_state.rows, chosen_index)
    engine_state.rows[chosen_index].cards = [Card(play.card_value)]
    next_row_cards = tuple(engine_state.rows[chosen_index].cards)

    resolution_step = TrickResolutionStep(
        action=StepAction.TOOK_ROW_SMALL,
        player_id=play.player_id,
        affected_row_id=row_id,
        played_card=Card(play.card_value),
        taken_cards=tuple(previous_cards),
        points_gained=bullheads,
        new_row_cards=next_row_cards,
    )
    next_shadow_state = apply_resolution_step(current_state, resolution_step)
    player_names = _player_names_for_state(current_state)
    row_chosen_event = build_presentation_row_chosen(
        player_id=play.player_id,
        player_names=player_names,
        row_id=row_id,
        card_value=play.card_value,
    )
    row_taken_event = build_presentation_row_taken(
        player_id=play.player_id,
        player_names=player_names,
        row_id=row_id,
        taken_cards=tuple(card.value for card in previous_cards),
        bullheads=bullheads,
        replacement_card_value=play.card_value,
        row_cards_after=tuple(card.value for card in next_row_cards),
    )

    resumed = TrickPresentationState(
        shadow_state=next_shadow_state,
        remaining_plays=state.remaining_plays,
        pending_row_choice=None,
        resolution_steps=state.resolution_steps + (resolution_step,),
        presentation_steps=state.presentation_steps
        + (
            _unchanged_presentation_step(row_chosen_event, current_state),
            _changed_presentation_step(row_taken_event, current_state, next_shadow_state),
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
            row_choice_required_event = build_presentation_row_choice_required(
                player_id=play.player_id,
                player_names=player_names,
                card_value=card.value,
            )
            return TrickPresentationState(
                shadow_state=current.shadow_state,
                remaining_plays=current.remaining_plays[1:],
                pending_row_choice=play,
                resolution_steps=current.resolution_steps,
                presentation_steps=current.presentation_steps
                + (
                    _unchanged_presentation_step(
                        row_choice_required_event,
                        current.shadow_state,
                    ),
                ),
            )

        row = current.shadow_state.rows[row_index]
        previous_cards = tuple(row.cards)
        engine_state = EnginePublicState.from_public_state(current.shadow_state)
        bullheads, taken = place_card(
            engine_state.rows,
            row_index,
            card,
            row_capacity=current.shadow_state.config.row_capacity,
        )
        next_row_cards = tuple(engine_state.rows[row_index].cards)
        resolution_step = TrickResolutionStep(
            action=StepAction.PLACED if taken is None else StepAction.TOOK_ROW_OVERFLOW,
            player_id=play.player_id,
            affected_row_id=row.row_id,
            played_card=card,
            taken_cards=tuple(previous_cards) if taken is not None else (),
            points_gained=bullheads if taken is not None else 0,
            new_row_cards=next_row_cards,
        )
        next_shadow_state = apply_resolution_step(current.shadow_state, resolution_step)
        presentation_event: PresentationEvent
        if taken is None:
            presentation_event = build_presentation_card_placed(
                player_id=play.player_id,
                player_names=player_names,
                card_value=card.value,
                row_id=row.row_id,
                row_cards_after=tuple(item.value for item in next_row_cards),
            )
        else:
            presentation_event = build_presentation_overflow_resolved(
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
            resolution_steps=current.resolution_steps + (resolution_step,),
            presentation_steps=current.presentation_steps
            + (
                _changed_presentation_step(
                    presentation_event,
                    current.shadow_state,
                    next_shadow_state,
                ),
            ),
        )
    if current.pending_row_choice is None and not current.remaining_plays:
        trick_finished_event = build_presentation_trick_finished()
        return TrickPresentationState(
            shadow_state=current.shadow_state,
            remaining_plays=current.remaining_plays,
            pending_row_choice=None,
            resolution_steps=current.resolution_steps,
            presentation_steps=current.presentation_steps
            + (
                _unchanged_presentation_step(
                    trick_finished_event,
                    current.shadow_state,
                ),
            ),
        )
    return current


def _unchanged_presentation_step(
    event: PresentationEvent,
    public_state: PublicState,
) -> PresentationStep:
    snapshot = _clone_public_state(public_state)
    return PresentationStep(
        event=event,
        public_state_before=snapshot,
        public_state_after=snapshot,
    )


def _changed_presentation_step(
    event: PresentationEvent,
    public_state_before: PublicState,
    public_state_after: PublicState,
) -> PresentationStep:
    return PresentationStep(
        event=event,
        public_state_before=_clone_public_state(public_state_before),
        public_state_after=_clone_public_state(public_state_after),
    )


def _clone_public_state(public_state: PublicState) -> PublicState:
    return EnginePublicState.from_public_state(public_state).to_public_state()


def _player_names_for_state(public_state: PublicState) -> dict[PlayerID, str]:
    return {player.player_id: player.name for player in public_state.players}
