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
    assert_no_visible_game_card_is_duplicated,
    assert_player_card_locations_are_consistent,
    assert_selectable_objects_are_visible,
    assert_visual_matches_public_state,
    assert_visual_state_is_consistent,
)
from row_taker.gui.game_visual_state import (
    GameVisualStep,
    PlayerPlayAnchor,
    RowCardAnchor,
    VisualHandCard,
    VisualMovingCard,
    VisualTransition,
)
from row_taker.gui.game_visual_transition import resolve_visual_step
from row_taker.gui_workbench.scenarios import get_scenario, scenarios
from row_taker.gui_workbench.timeline import get_timeline


@pytest.mark.parametrize("scenario", scenarios("game"), ids=lambda item: item.name)
def test_all_workbench_scenario_frames_are_consistent(scenario) -> None:
    for frame in scenario.interesting_frames:
        visual_state = build_game_visual_state(
            scenario.state,
            last_action_summary="test",
            presentation_elapsed_frames=frame,
        )

        assert_visual_state_is_consistent(visual_state)


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
            assert_visual_state_is_consistent(visual_state)
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
            replace(card, visible=True) if card.card_value == own_player.staged_card_value else card
            for card in state.hand
        ),
    )

    with pytest.raises(AssertionError, match="duplicated"):
        assert_no_visible_game_card_is_duplicated(broken)


def test_invariant_rejects_multiple_active_players() -> None:
    state = build_game_visual_state(
        get_scenario("cards-revealed").state,
        last_action_summary="test",
    )
    broken = replace(
        state,
        players=tuple(
            replace(player, emphasis="active") if index < 2 else player
            for index, player in enumerate(state.players)
        ),
    )

    with pytest.raises(AssertionError, match="multiple active players"):
        assert_player_card_locations_are_consistent(broken)


def test_invariant_rejects_card_in_player_tile_and_motion() -> None:
    state = build_game_visual_state(
        get_scenario("cards-revealed").state,
        last_action_summary="test",
    )
    player = next(player for player in state.players if player.staged_card_value is not None)
    card_value = player.staged_card_value
    assert card_value is not None
    target_row = state.rows[0]
    broken = replace(
        state,
        moving_cards=(
            VisualMovingCard(
                card_value=card_value,
                source=PlayerPlayAnchor(player.player_id, card_value),
                target=RowCardAnchor(target_row.row_id, len(target_row.cards)),
                progress=0.5,
            ),
        ),
    )

    with pytest.raises(AssertionError, match="tile and in motion"):
        assert_player_card_locations_are_consistent(broken)


def test_invariant_rejects_moving_own_card_still_visible_in_hand() -> None:
    state = build_game_visual_state(
        get_scenario("cards-revealed").state,
        last_action_summary="test",
    )
    own_player = state.own_player
    assert own_player is not None
    card_value = own_player.staged_card_value
    assert card_value is not None
    target_row = state.rows[0]
    broken = replace(
        state,
        players=tuple(
            replace(player, staged_card_value=None)
            if player.player_id == own_player.player_id
            else player
            for player in state.players
        ),
        hand=tuple(
            replace(card, visible=True) if card.card_value == card_value else card
            for card in state.hand
        ),
        moving_cards=(
            VisualMovingCard(
                card_value=card_value,
                source=PlayerPlayAnchor(own_player.player_id, card_value),
                target=RowCardAnchor(target_row.row_id, len(target_row.cards)),
                progress=0.5,
            ),
        ),
    )

    with pytest.raises(AssertionError, match="moving own card"):
        assert_player_card_locations_are_consistent(broken)


def test_visual_transition_validates_completed_after_state() -> None:
    state = build_game_visual_state(
        get_scenario("choose-card").state,
        last_action_summary="test",
    )
    broken_after = replace(
        state,
        players=tuple(
            replace(player, emphasis="active") if index < 2 else player
            for index, player in enumerate(state.players)
        ),
    )
    step = GameVisualStep(
        before=state,
        after=broken_after,
        transition=VisualTransition(duration_frames=1),
    )

    with pytest.raises(AssertionError, match="multiple active players"):
        resolve_visual_step(step, presentation_elapsed_frames=1)
