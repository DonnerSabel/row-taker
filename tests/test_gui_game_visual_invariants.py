from __future__ import annotations

from dataclasses import replace

import pytest

from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationOverflowResolved,
    PresentationRowTaken,
)
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui.game_visual_invariants import (
    assert_motion_anchors_are_resolvable,
    assert_no_visible_game_card_is_duplicated,
    assert_selectable_objects_are_visible,
    assert_visual_matches_public_state,
)
from row_taker.gui.game_visual_state import VisualHandCard
from row_taker.gui_workbench.scenarios import get_scenario, scenarios
from row_taker.gui_workbench.timeline import get_timeline


@pytest.mark.parametrize("scenario", scenarios("game"), ids=lambda item: item.name)
def test_all_workbench_scenarios_have_visible_interaction_targets(scenario) -> None:
    visual_state = build_game_visual_state(
        scenario.state,
        last_action_summary="test",
        presentation_elapsed_frames=16,
    )

    assert_selectable_objects_are_visible(visual_state)
    assert_motion_anchors_are_resolvable(visual_state)


def test_full_timeline_visual_states_match_their_snapshots() -> None:
    timeline = get_timeline("full-trick")
    changing_events = (
        PresentationCardPlaced,
        PresentationRowTaken,
        PresentationOverflowResolved,
    )

    for timeline_step in timeline.steps:
        state = timeline_step.state
        presentation_step = state.current_presentation_step
        for frame in timeline_step.interesting_frames:
            visual_state = build_game_visual_state(
                state,
                last_action_summary="test",
                presentation_elapsed_frames=frame,
            )
            assert_selectable_objects_are_visible(visual_state)
            assert_motion_anchors_are_resolvable(visual_state)
            assert_no_visible_game_card_is_duplicated(visual_state)

            if presentation_step is None:
                assert state.public_state is not None
                expected = state.public_state
            elif isinstance(presentation_step.event, changing_events) and frame < 32:
                expected = presentation_step.public_state_before
            else:
                expected = presentation_step.public_state_after
            assert_visual_matches_public_state(visual_state, expected)


def test_invariant_rejects_selectable_hidden_hand_card() -> None:
    state = build_game_visual_state(
        get_scenario("choose-card").state,
        last_action_summary="test",
    )
    hidden_value = next(iter(state.interaction.selectable_card_values))
    broken = replace(
        state,
        hand=tuple(
            replace(card, visible=False) if card.card_value == hidden_value else card
            for card in state.hand
        ),
    )

    with pytest.raises(AssertionError, match="not visible"):
        assert_selectable_objects_are_visible(broken)


def test_invariant_rejects_duplicate_visible_card() -> None:
    state = build_game_visual_state(
        get_scenario("choose-card").state,
        last_action_summary="test",
    )
    row_value = state.rows[0].cards[0]
    broken = replace(
        state,
        hand=state.hand
        + (
            VisualHandCard(
                card_value=row_value.card_value,
                bullheads=row_value.bullheads,
            ),
        ),
    )

    with pytest.raises(AssertionError, match="duplicated"):
        assert_no_visible_game_card_is_duplicated(broken)


def test_invariant_counts_staged_card_of_own_player() -> None:
    state = build_game_visual_state(
        get_scenario("cards-revealed").state,
        last_action_summary="test",
    )
    own_player = state.own_player
    assert own_player is not None
    assert own_player.staged_card_value is not None
    broken = replace(
        state,
        hand=tuple(
            replace(card, visible=True)
            if card.card_value == own_player.staged_card_value
            else card
            for card in state.hand
        ),
    )

    with pytest.raises(AssertionError, match="duplicated"):
        assert_no_visible_game_card_is_duplicated(broken)
