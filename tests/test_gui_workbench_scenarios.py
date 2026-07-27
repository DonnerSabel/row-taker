from __future__ import annotations

import pytest

from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationCardsRevealed,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
    PresentationRowTaken,
)
from row_taker.engine.game import Phase
from row_taker.gui_workbench.scenarios import get_scenario, scenario_names, scenarios


def test_workbench_scenario_catalog_is_stable_and_complete() -> None:
    assert scenario_names() == (
        "choose-card",
        "choose-row",
        "cards-revealed",
        "card-placed",
        "row-choice-required",
        "row-taken",
        "overflow-resolved",
        "long-names",
    )
    assert tuple(scenario.name for scenario in scenarios()) == scenario_names()


def test_get_scenario_returns_fresh_deterministic_state() -> None:
    first = get_scenario("choose-card")
    second = get_scenario("choose-card")

    assert first == second
    assert first is not second
    assert first.state is not second.state


def test_choose_row_scenario_uses_real_choose_row_state() -> None:
    scenario = get_scenario("choose-row")
    player_state = scenario.state.player_state

    assert player_state is not None
    assert scenario.state.pending_action == PendingAction.CHOOSE_ROW
    assert player_state.phase_info.phase == Phase.CHOOSE_ROW
    assert player_state.pending_card_value() == 7
    assert player_state.get_selectable_row_ids_for_choose_row() == tuple(
        row.row_id for row in player_state.rows
    )


@pytest.mark.parametrize(
    ("scenario_name", "event_type"),
    (
        ("cards-revealed", PresentationCardsRevealed),
        ("card-placed", PresentationCardPlaced),
        ("row-choice-required", PresentationRowChoiceRequired),
        ("row-taken", PresentationRowTaken),
        ("overflow-resolved", PresentationOverflowResolved),
    ),
)
def test_presentation_scenarios_put_expected_real_event_at_queue_front(
    scenario_name: str,
    event_type: type,
) -> None:
    scenario = get_scenario(scenario_name)

    assert scenario.state.pending_presentation_events
    assert isinstance(scenario.state.pending_presentation_events[0], event_type)


def test_row_choice_required_scenario_includes_real_choose_row_request_state() -> None:
    scenario = get_scenario("row-choice-required")
    player_state = scenario.state.player_state

    assert player_state is not None
    assert scenario.state.pending_action == PendingAction.CHOOSE_ROW
    assert player_state.phase_info.phase == Phase.CHOOSE_ROW
    assert player_state.pending_card_value() == 7


def test_unknown_scenario_has_actionable_error() -> None:
    with pytest.raises(KeyError, match="available: choose-card"):
        get_scenario("missing")
