from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationCardsRevealed,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.engine.game import Phase
from row_taker.gui_workbench.app import (
    WorkbenchApp,
    prepare_headless_pygame,
    render_scenario_frame,
    save_timeline_frames,
)
from row_taker.gui_workbench.timeline import get_timeline, timeline_names, timelines


@pytest.fixture(scope="module", autouse=True)
def initialized_pygame() -> None:
    prepare_headless_pygame()
    yield
    pygame.quit()


def _front_event_type(step):
    pending = step.state.pending_presentation_steps
    return None if not pending else type(pending[0].event)


def test_timeline_catalog_is_stable() -> None:
    assert timeline_names() == ("full-trick",)
    assert tuple(timeline.name for timeline in timelines()) == timeline_names()


def test_full_trick_uses_expected_real_state_sequence() -> None:
    timeline = get_timeline("full-trick")

    assert len(timeline.steps) == 11
    assert tuple(_front_event_type(step) for step in timeline.steps) == (
        None,
        PresentationCardsRevealed,
        PresentationRowChoiceRequired,
        None,
        PresentationRowChosen,
        PresentationRowTaken,
        PresentationOverflowResolved,
        PresentationCardPlaced,
        PresentationCardPlaced,
        PresentationTrickFinished,
        None,
    )

    choose_card = timeline.steps[0].state
    choose_row = timeline.steps[3].state
    final_state = timeline.steps[-1].state

    assert choose_card.pending_action == PendingAction.CHOOSE_CARD
    assert choose_row.pending_action == PendingAction.CHOOSE_ROW
    assert choose_row.player_state is not None
    assert choose_row.player_state.phase_info.phase == Phase.CHOOSE_ROW
    assert final_state.pending_action == PendingAction.CHOOSE_CARD
    assert final_state.pending_presentation_steps == ()
    assert final_state.public_state == timeline.expected_final_public_state
    assert final_state.public_state is not None
    assert final_state.public_state.phase_info.phase == Phase.CHOOSE_CARD


def test_full_trick_final_rows_and_scores_come_from_match_hub() -> None:
    timeline = get_timeline("full-trick")
    final = timeline.expected_final_public_state

    assert tuple(tuple(card.value for card in row.cards) for row in final.rows) == (
        (53, 66),
        (7,),
        (78,),
        (92, 95),
    )
    assert tuple((player.score, player.hand_count) for player in final.players) == (
        (2, 1),
        (15, 1),
        (0, 1),
        (0, 1),
    )


def test_every_timeline_step_renders_all_interesting_frames() -> None:
    timeline = get_timeline("full-trick")

    for step in timeline.steps:
        for frame in step.interesting_frames:
            rendered = render_scenario_frame(
                step,
                frame_count=frame,
                presentation_frame_count=frame,
            )
            assert rendered.surface.get_size() == timeline.default_size


def test_save_timeline_frames_exports_complete_sequence(tmp_path: Path) -> None:
    timeline = get_timeline("full-trick")

    outputs = save_timeline_frames(timeline, tmp_path)

    expected_count = sum(len(step.interesting_frames) for step in timeline.steps)
    assert len(outputs) == expected_count
    assert all(output.is_file() for output in outputs)
    assert outputs[0].name.startswith("full-trick_step_00_")
    assert any("row-chosen" in output.name for output in outputs)
    assert outputs[-1].name.startswith("full-trick_step_10_")


def test_interactive_timeline_navigation_resets_animation_clocks() -> None:
    timeline = get_timeline("full-trick")
    app = WorkbenchApp(
        timeline=timeline,
        frame_count=12,
        presentation_frame_count=8,
    )

    assert app.timeline_step_index == 0
    assert app.timeline_step_count == len(timeline.steps)
    assert app.current_scenario == timeline.steps[0]

    assert app.select_previous_step() is False
    assert app.select_next_step() is True
    assert app.timeline_step_index == 1
    assert app.current_scenario == timeline.steps[1]

    for _ in range(len(timeline.steps) + 2):
        app.select_next_step()
    assert app.timeline_step_index == len(timeline.steps) - 1
    assert app.select_next_step() is False


def test_unknown_timeline_has_actionable_error() -> None:
    with pytest.raises(KeyError, match="available: full-trick"):
        get_timeline("missing")
