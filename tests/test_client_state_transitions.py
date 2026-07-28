from __future__ import annotations

import inspect
from pathlib import Path

from client_test_support import player_state_for

from row_taker.client.core_state import ClientMode, PendingAction
from row_taker.client.state import (
    UiMessage,
    assign_identity,
    clear_bot_name_editor,
    clear_flash_message,
    enter_lobby_submenu,
    initial_client_state,
    mark_server_error,
    mark_session_ended,
    mark_transport_closed,
    request_card_choice,
    request_exit,
    select_bot_name_text,
    set_bot_name_editor,
    set_flash_message,
)

ROOT = Path(__file__).resolve().parents[1]


def test_state_transition_api_has_no_untyped_keyword_update_helpers() -> None:
    source = (ROOT / "src/row_taker/client/state.py").read_text(encoding="utf-8")

    assert "with_core_updates" not in source
    assert "with_navigation_updates" not in source
    assert "with_feedback_updates" not in source
    assert "**changes: object" not in source


def test_public_transition_functions_use_explicit_parameters() -> None:
    transitions = (
        assign_identity,
        clear_bot_name_editor,
        clear_flash_message,
        enter_lobby_submenu,
        mark_server_error,
        mark_session_ended,
        mark_transport_closed,
        request_card_choice,
        request_exit,
        select_bot_name_text,
        set_bot_name_editor,
        set_flash_message,
    )

    for transition in transitions:
        assert all(
            parameter.kind is not inspect.Parameter.VAR_KEYWORD
            for parameter in inspect.signature(transition).parameters.values()
        )


def test_request_card_choice_sets_the_complete_game_selection_state() -> None:
    player_state = player_state_for(0)
    state = set_flash_message(initial_client_state("client-a"), UiMessage("error", "alt"))

    updated = request_card_choice(state, player_state.self_player_id, player_state)

    assert updated.client_mode == ClientMode.GAME
    assert updated.pending_action == PendingAction.CHOOSE_CARD
    assert updated.own_player_id == player_state.self_player_id
    assert updated.player_state == player_state
    assert updated.public_state == player_state.public_state
    assert updated.presentation_steps == ()
    assert updated.pending_presentation_steps == ()
    assert updated.flash_message == UiMessage("error", "alt")


def test_feedback_transitions_change_only_the_named_feedback_concern() -> None:
    state = assign_identity(initial_client_state(), "client-a")
    state = set_flash_message(state, UiMessage("info", "Hallo"))

    cleared = clear_flash_message(state)
    exiting = request_exit(cleared, suppress_final_result=True)

    assert cleared.own_client_id == "client-a"
    assert cleared.flash_message is None
    assert exiting.should_exit is True
    assert exiting.suppress_final_result is True
    assert exiting.own_client_id == "client-a"


def test_session_failure_transitions_keep_their_distinct_exit_contracts() -> None:
    state = set_flash_message(initial_client_state(), UiMessage("info", "alt"))

    ended = mark_session_ended(state, "Sitzung beendet")
    failed = mark_server_error(state, "Serverfehler")
    disconnected = mark_transport_closed(state, "Verbindung beendet")

    assert ended.session_error == "Sitzung beendet"
    assert ended.should_exit is True
    assert ended.exit_on_ack is False
    assert ended.suppress_final_result is True
    assert ended.flash_message is None

    assert failed.session_error == "Serverfehler"
    assert failed.should_exit is False
    assert failed.exit_on_ack is True
    assert failed.suppress_final_result is True
    assert failed.flash_message is None

    assert disconnected.session_error == "Verbindung beendet"
    assert disconnected.exit_on_ack is False
    assert disconnected.flash_message == UiMessage("info", "alt")


def test_bot_name_editor_transitions_preserve_lobby_navigation() -> None:
    state = enter_lobby_submenu(initial_client_state(), "bot_name", selected_seat_index=2)
    state = set_bot_name_editor(state, text="Clara Bot", selected=False)

    selected = select_bot_name_text(state)
    cleared = clear_bot_name_editor(selected)

    assert selected.navigation_state.lobby_submenu == "bot_name"
    assert selected.navigation_state.selected_seat_index == 2
    assert selected.navigation_state.bot_name_text == "Clara Bot"
    assert selected.navigation_state.bot_name_selected is True

    assert cleared.navigation_state.lobby_submenu == "bot_name"
    assert cleared.navigation_state.selected_seat_index == 2
    assert cleared.navigation_state.bot_name_text == ""
    assert cleared.navigation_state.bot_name_selected is False
