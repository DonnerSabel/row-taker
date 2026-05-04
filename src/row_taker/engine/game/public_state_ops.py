from __future__ import annotations

from row_taker.engine.game.cards import Card
from row_taker.engine.game.state import EnginePublicState, PublicState, TrickResolutionStep


def played_card_from_step(step: TrickResolutionStep) -> Card:
    return step.played_card


def apply_resolution_step(public_state: PublicState, step: TrickResolutionStep) -> PublicState:
    engine_state = EnginePublicState.from_public_state(public_state)
    engine_state.apply_resolution_step(step)
    return engine_state.to_public_state()


def apply_resolution_steps(
    public_state: PublicState,
    steps: tuple[TrickResolutionStep, ...] | list[TrickResolutionStep],
) -> PublicState:
    current_state = public_state
    for step in steps:
        current_state = apply_resolution_step(current_state, step)
    return current_state
