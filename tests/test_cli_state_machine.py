from __future__ import annotations

from row_taker.client.core_state import ClientCoreState, PendingAction

import random

from row_taker.cli.frontend import CliFrontend, set_flash
from row_taker.cli.render import determine_prompt, render_resolution_lines
from row_taker.cli.screens import GameScreen, current_screen
from row_taker.client.core_reducer import reduce_server_message as direct_reduce_server_message
from row_taker.client.game_client_core import GameClientCore
from row_taker.client.presentation_events import PresentationCardsRevealed, PresentationRowTaken
from row_taker.client.state import ClientState, enter_game_mode, enter_lobby_submenu, with_feedback_updates
from row_taker.engine.game import build_player_state, setup_game
from row_taker.protocol.messages import (
    CardsRevealed,
    LeaveSession,
    PlayedCardView,
    RowChoiceCommitted,
    SessionEndReason,
    SessionEnded,
    StateUpdated,
)


_FRONTEND = CliFrontend()


def _player_state_for(index: int):
    game = setup_game(["A", "B"], rng=random.Random(123))
    player_id = game.players[index].player_id
    return build_player_state(game, player_id)


def _apply_server_message(state: ClientState, message) -> ClientState:
    from row_taker.protocol.messages import ChooseCardRequested, RowChoiceCommitted

    if isinstance(message, (RowChoiceCommitted, ChooseCardRequested)):
        return direct_reduce_server_message(state, message)
    core = GameClientCore(state)
    core.on_server_message(message)
    return core.state


def _restore_interaction_context(
    state: ClientState,
    *,
    previous_submenu: str,
    previous_seat_index: int | None,
    previous_action: PendingAction,
) -> ClientState:
    if state.client_mode.value == "lobby":
        if previous_submenu == "main":
            return enter_lobby_submenu(state, "main")
        if previous_submenu == "rename":
            return enter_lobby_submenu(state, "rename")
        if previous_submenu == "seat_edit":
            assert previous_seat_index is not None
            return enter_lobby_submenu(state, "seat_edit", selected_seat_index=previous_seat_index)
        if previous_submenu == "bot_name":
            assert previous_seat_index is not None
            return enter_lobby_submenu(state, "bot_name", selected_seat_index=previous_seat_index)
        raise AssertionError(f"unexpected submenu: {previous_submenu!r}")

    if previous_action == PendingAction.CHOOSE_CARD:
        assert state.player_state is not None
        return enter_game_mode(state, pending_action=PendingAction.CHOOSE_CARD, player_state=state.player_state)
    if previous_action == PendingAction.CHOOSE_ROW:
        assert state.player_state is not None
        return enter_game_mode(state, pending_action=PendingAction.CHOOSE_ROW, player_state=state.player_state)
    return enter_game_mode(state, pending_action=PendingAction.NONE, player_state=state.player_state)


def _apply_user_input(state: ClientState, text: str):
    previous_submenu = state.navigation_state.lobby_submenu
    previous_seat_index = state.navigation_state.selected_seat_index
    previous_action = state.pending_action
    parsed = _FRONTEND.handle_text_input(state, text)
    state = parsed.state
    if parsed.action is None:
        return state, None
    core = GameClientCore(state)
    update = core.on_ui_action(parsed.action)
    state = core.state
    if update.local_messages:
        state = with_feedback_updates(state, flash_message=None)
        state = _restore_interaction_context(
            state,
            previous_submenu=previous_submenu,
            previous_seat_index=previous_seat_index,
            previous_action=previous_action,
        )
        state = set_flash(state, "error", update.local_messages[-1])
        return state, None
    outbound = update.outbound_messages[0] if update.outbound_messages else None
    return state, outbound


def test_state_updated_sets_public_state() -> None:
    player_state = _player_state_for(0)
    state = ClientState()

    new_state = _apply_server_message(state, StateUpdated(state=player_state.public_state))
    assert new_state.public_state == player_state.public_state


def test_choose_card_requested_enters_choose_card_screen() -> None:
    player_state = _player_state_for(0)
    state = ClientState()

    from row_taker.protocol.messages import ChooseCardRequested

    new_state = _apply_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.own_player_id == player_state.self_player_id
    assert isinstance(current_screen(new_state), GameScreen)
    assert current_screen(new_state).kind == "choose_card"


def test_cards_revealed_is_stored_for_waiting_screen() -> None:
    player_state = _player_state_for(0)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.self_player_id,
                player_name=player_state.self_player_name(),
                card_value=player_state.hand[0].value,
            ),
        ),
    )

    state = _apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.public_state == player_state.public_state
    assert state.revealed_trick == revealed


def test_uppercase_x_triggers_leave_session_and_suppresses_final_result() -> None:
    state, outbound = _apply_user_input(ClientState(), "X")

    assert outbound == LeaveSession()
    assert state.should_exit is True
    assert state.suppress_final_result is True


def test_session_ended_exits_immediately() -> None:
    state = _apply_server_message(
        ClientState(),
        SessionEnded(message="Spiel abgebrochen", reason=SessionEndReason.QUIT, client_id="client-0", display_name="Alice"),
    )

    assert state.should_exit is True
    assert state.session_error == "Spiel abgebrochen"


def test_cards_revealed_builds_local_presentation_events() -> None:
    player_state = _player_state_for(0)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.public_state.players[0].player_id,
                player_name=player_state.public_state.players[0].name,
                card_value=104,
            ),
            PlayedCardView(
                player_id=player_state.public_state.players[1].player_id,
                player_name=player_state.public_state.players[1].name,
                card_value=103,
            ),
        ),
    )

    state = _apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.trick_presentation_state is not None
    assert state.pending_presentation_events
    assert isinstance(state.pending_presentation_events[0], PresentationCardsRevealed)


def test_row_choice_committed_advances_trick_presentation_state() -> None:
    player_state = _player_state_for(0)
    lowest = min(row.cards[-1].value for row in player_state.public_state.rows)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.self_player_id,
                player_name=player_state.self_player_name(),
                card_value=lowest - 1,
            ),
        ),
    )

    state = _apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)
    assert state.trick_presentation_state is not None
    assert state.trick_presentation_state.pending_row_choice is not None

    row_id = player_state.public_state.rows[0].row_id
    state = _apply_server_message(state, RowChoiceCommitted(row_id=row_id))

    assert state.trick_presentation_state is not None
    assert state.trick_presentation_state.pending_row_choice is None
    assert any(isinstance(event, PresentationRowTaken) for event in state.pending_presentation_events)


def test_cards_revealed_queues_presentation_events_before_display() -> None:
    player_state = _player_state_for(0)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.public_state.players[0].player_id,
                player_name=player_state.public_state.players[0].name,
                card_value=104,
            ),
        ),
    )

    state = _apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.presentation_events == ()
    assert state.pending_presentation_events


def test_pending_presentation_uses_enter_prompt_until_queue_is_empty() -> None:
    state = ClientState(
        core_state=ClientCoreState(pending_presentation_events=(PresentationCardsRevealed(plays=()),)),
    )
    state = enter_game_mode(state, pending_action=PendingAction.CHOOSE_ROW, player_state=_player_state_for(0))

    assert determine_prompt(state) == "Weiter mit Enter > "


def test_enter_advances_pending_presentation_queue() -> None:
    state = ClientState(
        core_state=ClientCoreState(
            pending_presentation_events=(PresentationCardsRevealed(plays=()), PresentationRowTaken("p1", "Alice", 1, (1, 2), 3, 5, (5,))),
        ),
    )
    state = enter_game_mode(state, pending_action=PendingAction.NONE)

    state, _ = _apply_user_input(state, "")

    assert len(state.presentation_events) == 1
    assert len(state.pending_presentation_events) == 1


def test_non_enter_during_pending_presentation_shows_hint() -> None:
    state = ClientState(
        core_state=ClientCoreState(pending_presentation_events=(PresentationCardsRevealed(plays=()),)),
    )
    state = enter_game_mode(state, pending_action=PendingAction.NONE)

    state, _ = _apply_user_input(state, "foo")

    assert state.flash_message is not None
    assert "Enter" in state.flash_message.text


def test_choose_card_requested_clears_visible_and_pending_presentation() -> None:
    player_state = _player_state_for(0)
    state = ClientState(
        core_state=ClientCoreState(
            public_state=player_state.public_state,
            presentation_events=(PresentationCardsRevealed(plays=()),),
            pending_presentation_events=(PresentationCardsRevealed(plays=()),),
        ),
    )

    from row_taker.protocol.messages import ChooseCardRequested

    new_state = _apply_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.presentation_events == ()
    assert new_state.pending_presentation_events == ()


def test_render_resolution_lines_renders_from_presentation_events() -> None:
    state = ClientState(core_state=ClientCoreState(own_player_id="p1", presentation_events=(PresentationCardsRevealed(plays=()),)))

    rendered = render_resolution_lines(state)
    assert rendered is not None
    assert "Lokale Auflösung" in rendered
