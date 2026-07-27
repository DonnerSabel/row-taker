from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame")

from row_taker.client.core_reducer import advance_presentation_queue
from row_taker.gui.board_layout import hand_card_placements, row_card_placements
from row_taker.gui.presentation_renderer import resolve_visual_card_motion_rects
from row_taker.gui.screens.game_screen import GameFrame, _opponent_slot_data
from row_taker.gui.layout import compute_layout
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
        frame_count=16,
        presentation_frame_count=16,
        last_action_summary="test",
        mouse_pos=(-1, -1),
    )
    moving_card = frame.visual_state.moving_cards[0]

    resolved = resolve_visual_card_motion_rects(
        frame.geometry,
        frame.visual_state,
        moving_card,
        opponent_slots=_opponent_slot_data(frame.visual_state, frame.geometry),
    )

    assert resolved is not None
    source_rect, target_rect = resolved
    if moving_card.source.player_id == frame.visual_state.own_player_id:
        hand_index = next(
            index
            for index, card in enumerate(frame.visual_state.hand)
            if card.card_value == moving_card.source.card_value
        )
        expected_source = hand_card_placements(
            frame.geometry,
            card_count=len(frame.visual_state.hand),
        )[hand_index].rect
        assert source_rect == expected_source

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
        frame_count=16,
        presentation_frame_count=16,
        last_action_summary="test",
        mouse_pos=(-1, -1),
    )
    moving_card = frame.visual_state.moving_cards[0]
    assert moving_card.source.player_id != frame.visual_state.own_player_id
    opponent_slots = _opponent_slot_data(frame.visual_state, frame.geometry)

    resolved = resolve_visual_card_motion_rects(
        frame.geometry,
        frame.visual_state,
        moving_card,
        opponent_slots=opponent_slots,
    )

    assert resolved is not None
    source_rect, _target_rect = resolved
    expected_slot = next(
        slot
        for slot in opponent_slots
        if slot.player_id == moving_card.source.player_id
    )
    assert source_rect == expected_slot.geometry.staged_card.rect


def test_own_card_motion_uses_hand_area_fallback_after_server_removed_card() -> None:
    timeline = get_timeline("full-trick")
    state = timeline.steps[5].state
    frame = GameFrame.from_layout(
        layout=compute_layout(1600, 900),
        state=state,
        frame_count=16,
        presentation_frame_count=16,
        last_action_summary="test",
        mouse_pos=(-1, -1),
    )
    moving_card = frame.visual_state.moving_cards[0]
    assert moving_card.source.player_id == frame.visual_state.own_player_id
    assert all(
        card.card_value != moving_card.source.card_value
        for card in frame.visual_state.hand
    )

    resolved = resolve_visual_card_motion_rects(
        frame.geometry,
        frame.visual_state,
        moving_card,
        opponent_slots=_opponent_slot_data(frame.visual_state, frame.geometry),
    )

    assert resolved is not None
    source_rect, _target_rect = resolved
    assert source_rect.size == frame.geometry.staged_card_size
    assert source_rect.center == frame.geometry.hand_rect.center
