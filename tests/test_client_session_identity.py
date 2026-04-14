from __future__ import annotations

from dataclasses import replace

from row_taker.cli.frontend import CliFrontend, set_flash
from row_taker.cli.render import render_screen
from row_taker.cli.state_models import CliState, LobbyScreen
from row_taker.client.game_client_core import GameClientCore
from row_taker.protocol.messages import (
    AssignSeatToClient,
    IdentityAssigned,
    LobbyParticipantView,
    LobbySeatView,
    LobbyStateUpdated,
    LobbyView,
)


_FRONTEND = CliFrontend()


def _lobby() -> LobbyView:
    return LobbyView(
        seat_count=3,
        participants=(
            LobbyParticipantView(
                client_id="client-1",
                display_name="Alice",
                participant_kind="human",
                seat_index=None,
            ),
            LobbyParticipantView(
                client_id="client-2", display_name="Bob", participant_kind="human", seat_index=1
            ),
            LobbyParticipantView(
                client_id="pending-bot-seat-2",
                display_name="Bot_1",
                participant_kind="bot",
                seat_index=2,
            ),
        ),
        seats=(
            LobbySeatView(
                seat_index=0,
                occupant_client_id=None,
                occupant_display_name=None,
                occupant_kind=None,
            ),
            LobbySeatView(
                seat_index=1,
                occupant_client_id="client-2",
                occupant_display_name="Bob",
                occupant_kind="human",
            ),
            LobbySeatView(
                seat_index=2,
                occupant_client_id="pending-bot-seat-2",
                occupant_display_name="Bot_1",
                occupant_kind="bot",
            ),
        ),
        game_started=False,
    )


def _apply_server_message(state: CliState, message) -> CliState:
    core = GameClientCore(state)
    update = core.on_server_message(message)
    return core.state


def _apply_user_input(state: CliState, text: str):
    previous_screen = state.screen
    parsed = _FRONTEND.handle_text_input(state, text)
    state = parsed.state
    if parsed.action is None:
        return state, None
    core = GameClientCore(state)
    update = core.on_ui_action(parsed.action)
    state = core.state
    if update.local_messages:
        state = replace(state, screen=previous_screen)
        state = set_flash(state, "error", update.local_messages[-1])
        return state, None
    outbound = update.outbound_messages[0] if update.outbound_messages else None
    return state, outbound


def test_reduce_server_message_stores_own_client_id_from_identity_assigned() -> None:
    state = CliState()

    new_state = _apply_server_message(state, IdentityAssigned(client_id="client-1"))

    assert new_state.own_client_id == "client-1"
    assert new_state.screen == LobbyScreen(kind="main")


def test_reduce_user_input_assign_seat_uses_explicit_own_client_id() -> None:
    state = CliState(
        own_client_id="client-1",
        lobby_view=_lobby(),
        screen=LobbyScreen(kind="seat_edit", seat_index=0),
    )

    state, outbound = _apply_user_input(state, "m")

    assert state.screen == LobbyScreen(kind="main")
    assert outbound == AssignSeatToClient(seat_index=0, target_client_id="client-1")


def test_reduce_user_input_assign_seat_without_identity_sets_local_error() -> None:
    state = CliState(
        lobby_view=_lobby(),
        screen=LobbyScreen(kind="seat_edit", seat_index=0),
    )

    state, outbound = _apply_user_input(state, "m")

    assert outbound is None
    assert state.screen == LobbyScreen(kind="seat_edit", seat_index=0)
    assert "client_id" in (state.flash_message.text if state.flash_message else "")


def test_render_lobby_shows_participants_and_marks_own_client() -> None:
    state = CliState(
        own_client_id="client-1",
        lobby_view=_lobby(),
        screen=LobbyScreen(kind="main"),
    )

    out = render_screen(state)
    assert "Teilnehmer" in out
    assert "Alice (human, nicht gesetzt) <- du" in out
    assert "Bob (human, Platz 1)" in out
    assert "Bot_1 (bot, Platz 2)" in out


def test_reduce_server_message_lobby_update_keeps_active_lobby_mode() -> None:
    state = CliState(
        own_client_id="client-1",
        screen=LobbyScreen(kind="seat_edit", seat_index=2),
    )

    new_state = _apply_server_message(state, LobbyStateUpdated(lobby=_lobby()))

    assert new_state.lobby_view == _lobby()
    assert new_state.screen == LobbyScreen(kind="seat_edit", seat_index=2)
