from __future__ import annotations

from dataclasses import replace

from row_taker.gui.game_visual_invariants import assert_motion_anchors_are_resolvable
from row_taker.gui.game_visual_state import (
    GameVisualState,
    GameVisualStep,
    VisualMovingCard,
)


def resolve_visual_step(
    step: GameVisualStep,
    *,
    presentation_frame_count: int,
) -> GameVisualState:
    """Resolve one visual before/after step at a deterministic frame."""

    duration = max(1, step.transition.duration_frames)
    progress = max(0.0, min(1.0, presentation_frame_count / duration))
    if progress >= 1.0:
        return step.after

    eased_progress = 1.0 - (1.0 - progress) ** 3
    moving_cards = tuple(
        VisualMovingCard(
            card_value=motion.card_value,
            source=motion.source,
            target=motion.target,
            progress=eased_progress,
        )
        for motion in step.transition.card_motions
    )
    visual_state = replace(step.before, moving_cards=moving_cards)
    assert_motion_anchors_are_resolvable(visual_state)
    return visual_state
