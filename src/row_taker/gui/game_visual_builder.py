from __future__ import annotations

from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationGameFinished,
    PresentationOverflowResolved,
    PresentationRoundFinished,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.client.state import ClientState
from row_taker.gui.game_visual_presentations import (
    build_card_placed_visual_step,
    build_finished_visual_state,
    build_row_choice_visual_state,
    build_row_replacement_visual_step,
)
from row_taker.gui.game_visual_state import GameVisualState
from row_taker.gui.game_visual_static import build_stable_game_visual_state
from row_taker.gui.game_visual_transition import resolve_visual_step


def build_game_visual_state(
    state: ClientState,
    *,
    presentation_elapsed_frames: int = 0,
) -> GameVisualState:
    """Translate client semantics into the complete game-screen model."""

    current_step = state.current_presentation_step
    if current_step is not None and isinstance(
        current_step.event,
        PresentationCardPlaced,
    ):
        visual_step = build_card_placed_visual_step(state)
        return resolve_visual_step(
            visual_step,
            presentation_elapsed_frames=presentation_elapsed_frames,
        )
    if current_step is not None and isinstance(
        current_step.event,
        PresentationRowTaken | PresentationOverflowResolved,
    ):
        visual_step = build_row_replacement_visual_step(state)
        return resolve_visual_step(
            visual_step,
            presentation_elapsed_frames=presentation_elapsed_frames,
        )
    if current_step is not None and isinstance(
        current_step.event,
        PresentationRowChoiceRequired | PresentationRowChosen,
    ):
        return build_row_choice_visual_state(state)
    if current_step is not None and isinstance(
        current_step.event,
        PresentationTrickFinished | PresentationRoundFinished | PresentationGameFinished,
    ):
        return build_finished_visual_state(state)

    return build_stable_game_visual_state(
        state,
        public_state=state.public_state,
    )
