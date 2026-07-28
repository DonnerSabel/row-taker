from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame")

from row_taker.client.presentation_queue import advance_presentation_queue
from row_taker.gui.board_layout import row_card_placements
from row_taker.gui.layout import compute_layout
from row_taker.gui.presentation_renderer import resolve_visual_card_motion_rects
from row_taker.gui.rendering.game_hud_renderer import player_staged_card_rects
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui_workbench.scenarios import get_scenario
from row_taker.gui_workbench.timeline import get_timeline


@pytest.mark.parametrize("scenario_name", ["card-placed", "row-taken"])
@pytest.mark.parametrize("size", [(1280, 720), (1600, 900)])
def test_semantic_card_motion_anchors_resolve_to_real_layout(
    scenario_name: str,
    size: tuple[int, int],
) -> None:
    state = get_scenario(scenario_name).state
    frame = GameFrame.from_layout(
        layout=compute_layout(*size),
        state=state,
        presentation_elapsed_frames=16,
        mouse_pos=(-1, -1),
    )
    moving_card = frame.visual_state.moving_cards[0]

    resolved = resolve_visual_card_motion_rects(
        frame.geometry,
        frame.visual_state,
        moving_card,
        player_staged_card_rects=player_staged_card_rects(
            frame.visual_state,
            frame.geometry,
        ),
    )

    assert resolved is not None
    source_rect, target_rect = resolved
    staged_rects = player_staged_card_rects(
        frame.visual_state,
        frame.geometry,
    )
    assert source_rect == staged_rects[moving_card.source.player_id]

    row_index = next(
        index
        for index, row in enumerate(frame.visual_state.rows)
        if row.row_id == moving_card.target.row_id
    )
    expected_target = row_card_placements(
        frame.geometry,
        row_index=row_index,
        card_count=max(
            len(frame.visual_state.rows[row_index].cards),
            moving_card.target.card_index + 1,
        ),
    )[moving_card.target.card_index].rect
    assert target_rect == expected_target


def test_opponent_card_motion_starts_at_real_staged_card_slot() -> None:
    state = advance_presentation_queue(get_scenario("card-placed").state)
    frame = GameFrame.from_layout(
        layout=compute_layout(1600, 900),
        state=state,
        presentation_elapsed_frames=16,
        mouse_pos=(-1, -1),
    )
    moving_card = frame.visual_state.moving_cards[0]
    assert moving_card.source.player_id != frame.visual_state.own_player_id
    staged_rects = player_staged_card_rects(frame.visual_state, frame.geometry)

    resolved = resolve_visual_card_motion_rects(
        frame.geometry,
        frame.visual_state,
        moving_card,
        player_staged_card_rects=staged_rects,
    )

    assert resolved is not None
    source_rect, _target_rect = resolved
    assert source_rect == staged_rects[moving_card.source.player_id]


def test_own_card_motion_starts_at_own_player_tile() -> None:
    timeline = get_timeline("full-trick")
    state = timeline.steps[5].state
    frame = GameFrame.from_layout(
        layout=compute_layout(1600, 900),
        state=state,
        presentation_elapsed_frames=16,
        mouse_pos=(-1, -1),
    )
    moving_card = frame.visual_state.moving_cards[0]
    assert moving_card.source.player_id == frame.visual_state.own_player_id
    assert all(card.card_value != moving_card.source.card_value for card in frame.visual_state.hand)

    resolved = resolve_visual_card_motion_rects(
        frame.geometry,
        frame.visual_state,
        moving_card,
        player_staged_card_rects=player_staged_card_rects(
            frame.visual_state,
            frame.geometry,
        ),
    )

    assert resolved is not None
    source_rect, _target_rect = resolved
    assert source_rect == frame.geometry.own_player_tile.card_placement.rect
