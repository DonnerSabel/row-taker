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
from row_taker.gui_workbench.scenarios import (
    ConnectWorkbenchScenario,
    GameWorkbenchScenario,
    LobbyWorkbenchScenario,
    get_scenario,
    scenario_category,
    scenario_names,
    scenarios,
)


def test_workbench_scenario_catalog_is_stable_and_grouped() -> None:
    assert scenario_names("connect") == (
        "connect-default",
        "connect-invalid-values",
        "connect-error",
        "connect-long-values",
    )
    assert scenario_names("lobby") == (
        "lobby-empty",
        "lobby-waiting",
        "lobby-seat-selected",
        "lobby-bot-name-edit",
        "lobby-full",
        "lobby-long-names",
    )
    assert scenario_names("game") == (
        "choose-card",
        "choose-row",
        "cards-revealed",
        "card-placed",
        "row-choice-required",
        "row-taken",
        "overflow-resolved",
        "long-names",
        "five-opponents",
        "five-opponents-revealed",
        "five-opponents-active",
        "own-player-active",
        "own-card-revealed",
        "presentation-click-required",
        "long-names-five-opponents",
    )
    assert tuple(scenario.name for scenario in scenarios()) == scenario_names()


def test_scenario_types_match_their_categories() -> None:
    assert all(isinstance(item, ConnectWorkbenchScenario) for item in scenarios("connect"))
    assert all(isinstance(item, LobbyWorkbenchScenario) for item in scenarios("lobby"))
    assert all(isinstance(item, GameWorkbenchScenario) for item in scenarios("game"))
    assert {scenario_category(item) for item in scenarios()} == {"connect", "lobby", "game"}


def test_get_scenario_returns_fresh_deterministic_input() -> None:
    first = get_scenario("choose-card")
    second = get_scenario("choose-card")

    assert first == second
    assert first is not second
    assert isinstance(first, GameWorkbenchScenario)
    assert first.state is not second.state


def test_connect_scenarios_cover_validation_error_and_long_values() -> None:
    invalid = get_scenario("connect-invalid-values")
    failed = get_scenario("connect-error")
    long_values = get_scenario("connect-long-values")

    assert isinstance(invalid, ConnectWorkbenchScenario)
    assert invalid.connect_form.error_message is not None
    assert failed.connect_form.error_message is not None
    assert len(long_values.connect_form.display_name) > 30


def test_lobby_scenarios_cover_selection_bot_edit_and_full_lobby() -> None:
    selected = get_scenario("lobby-seat-selected")
    bot_edit = get_scenario("lobby-bot-name-edit")
    full = get_scenario("lobby-full")

    assert isinstance(selected, LobbyWorkbenchScenario)
    assert selected.state.navigation_state.selected_seat_index == 1
    assert bot_edit.state.navigation_state.lobby_submenu == "bot_name"
    assert bot_edit.state.navigation_state.bot_name_selected is True
    assert full.state.lobby_view is not None
    assert all(seat.occupant_display_name is not None for seat in full.state.lobby_view.seats)


def test_choose_row_scenario_uses_real_choose_row_state() -> None:
    scenario = get_scenario("choose-row")
    assert isinstance(scenario, GameWorkbenchScenario)
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
    assert isinstance(scenario, GameWorkbenchScenario)

    assert scenario.state.pending_presentation_steps
    assert isinstance(scenario.state.pending_presentation_steps[0].event, event_type)


def test_row_choice_required_scenario_includes_real_choose_row_request_state() -> None:
    scenario = get_scenario("row-choice-required")
    assert isinstance(scenario, GameWorkbenchScenario)
    player_state = scenario.state.player_state

    assert player_state is not None
    assert scenario.state.pending_action == PendingAction.CHOOSE_ROW
    assert player_state.phase_info.phase == Phase.CHOOSE_ROW
    assert player_state.pending_card_value() == 7


def test_maximum_player_scenarios_really_contain_five_opponents() -> None:
    for name in (
        "five-opponents",
        "five-opponents-revealed",
        "five-opponents-active",
        "long-names-five-opponents",
    ):
        scenario = get_scenario(name)
        assert isinstance(scenario, GameWorkbenchScenario)
        assert scenario.state.public_state is not None
        assert len(scenario.state.public_state.players) == 6


def test_unknown_scenario_has_actionable_error() -> None:
    with pytest.raises(KeyError, match="available: connect-default"):
        get_scenario("missing")
