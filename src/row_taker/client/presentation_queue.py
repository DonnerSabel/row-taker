from __future__ import annotations

from dataclasses import replace

from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import ClientState


def append_pending_presentation_steps(
    state: ClientState,
    steps: tuple[PresentationStep, ...],
) -> ClientState:
    if not steps:
        return state
    return replace(
        state,
        core_state=replace(
            state.core_state,
            pending_presentation_steps=state.pending_presentation_steps + steps,
        ),
    )


def advance_presentation_queue(state: ClientState) -> ClientState:
    if not state.pending_presentation_steps:
        return state
    next_step = state.pending_presentation_steps[0]
    return replace(
        state,
        core_state=replace(
            state.core_state,
            presentation_steps=state.presentation_steps + (next_step,),
            pending_presentation_steps=state.pending_presentation_steps[1:],
        ),
    )
