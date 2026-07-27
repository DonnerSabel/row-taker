from __future__ import annotations

from dataclasses import replace

import pytest

from row_taker.client.presentation_events import (
    PresentationGameFinished,
    PresentationOverflowResolved,
    PresentationRoundFinished,
    PresentationTrickFinished,
)
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui.game_visual_state import PlayerPlayAnchor, RowCardAnchor
from row_taker.gui_workbench.scenarios import get_scenario
from row_taker.gui_workbench.timeline import get_timeline


def test_overflow_uses_before_and_after_snapshots_with_one_motion() -> None:
    state = get_scenario("overflow-resolved").state
    step = state.current_presentation_step
    assert step is not None
    assert isinstance(step.event, PresentationOverflowResolved)
    event = step.event

    before = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_frame_count=0,
    )
    middle = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_frame_count=16,
    )
    after = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_frame_count=32,
    )

    before_row = before.row_by_id(event.row_id)
    after_row = after.row_by_id(event.row_id)
    assert before_row is not None
    assert after_row is not None
    assert before_row.card_values == event.taken_cards
    assert before_row.emphasis == "overflow"
    assert before_row.card_values == tuple(
        card.card_value for card in before_row.taken_cards
    )
    assert after_row.card_values == event.row_cards_after == (event.card_value,)
    assert after_row.emphasis == "overflow"

    assert len(middle.moving_cards) == 1
    motion = middle.moving_cards[0]
    assert motion.card_value == event.card_value
    assert motion.source == PlayerPlayAnchor(event.player_id, event.card_value)
    assert motion.target == RowCardAnchor(event.row_id, 0)
    assert motion.progress == 0.875
    assert after.moving_cards == ()

    before_player = next(
        player for player in before.players if player.player_id == event.player_id
    )
    after_player = next(
        player for player in after.players if player.player_id == event.player_id
    )
    assert before_player.score + event.bullheads == after_player.score
    assert before_player.staged_card_value is None
    if event.player_id == state.own_player_id:
        own_card = next(card for card in middle.hand if card.card_value == event.card_value)
        assert own_card.visible is False

    assert middle.presentation_panel is not None
    assert (
        middle.presentation_panel.headline
        == f"Overflow: {event.player_name} nimmt Reihe {event.row_id}"
    )
    assert middle.presentation_panel.card_values == (event.card_value,)


@pytest.mark.parametrize(
    ("event", "headline"),
    [
        (PresentationTrickFinished(), "Stich beendet"),
        (PresentationRoundFinished(), "Runde beendet"),
        (PresentationGameFinished(), "Spiel beendet"),
    ],
)
def test_finish_events_are_complete_visual_states(event, headline: str) -> None:
    state = get_timeline("full-trick").steps[9].state
    current_step = state.current_presentation_step
    assert current_step is not None
    custom_step = replace(current_step, event=event)
    state = replace(
        state,
        core_state=replace(
            state.core_state,
            pending_presentation_steps=(custom_step,),
        ),
    )

    visual_state = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_frame_count=16,
    )

    assert visual_state.presentation_panel is not None
    assert visual_state.presentation_panel.headline == headline
    assert visual_state.presentation_panel.card_values == ()
    assert visual_state.interaction.can_advance_presentation is True
    assert visual_state.moving_cards == ()
    assert all(player.staged_card_value is None for player in visual_state.players)
    completed_own_cards = {
        step.event.card_value
        for step in state.presentation_steps
        if hasattr(step.event, "card_value")
        and getattr(step.event, "player_id", None) == state.own_player_id
    }
    completed_own_cards.update(
        step.event.replacement_card_value
        for step in state.presentation_steps
        if hasattr(step.event, "replacement_card_value")
        and getattr(step.event, "player_id", None) == state.own_player_id
    )
    assert all(
        card.visible is False
        for card in visual_state.hand
        if card.card_value in completed_own_cards
    )
