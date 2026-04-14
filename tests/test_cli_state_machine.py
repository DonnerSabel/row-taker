from __future__ import annotations

from dataclasses import replace

from row_taker.client.core_state import ClientCoreState

import random

from row_taker.cli.frontend import CliFrontend, set_flash
from row_taker.cli.render import determine_prompt, render_resolution_lines
from row_taker.cli.state_models import CliState, GameScreen, with_screen
from row_taker.client.game_client_core import GameClientCore
from row_taker.client.core_reducer import reduce_server_message as direct_reduce_server_message
from row_taker.client.presentation_events import PresentationCardsRevealed, PresentationRowTaken
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


def _apply_server_message(state: CliState, message) -> CliState:
    from row_taker.protocol.messages import ChooseCardRequested, RowChoiceCommitted

    if isinstance(message, (RowChoiceCommitted, ChooseCardRequested)):
        return direct_reduce_server_message(state, message)
    core = GameClientCore(state)
    core.on_server_message(message)
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
        state = with_screen(state, previous_screen)
        state = set_flash(state, "error", update.local_messages[-1])
        return state, None
    outbound = update.outbound_messages[0] if update.outbound_messages else None
    return state, outbound


def test_state_updated_sets_public_state() -> None:
    player_state = _player_state_for(0)
    state = CliState()

    new_state = _apply_server_message(state, StateUpdated(state=player_state.public_state))
    assert new_state.public_state == player_state.public_state


def test_choose_card_requested_enters_choose_card_screen() -> None:
    player_state = _player_state_for(0)
    state = CliState()

    from row_taker.protocol.messages import ChooseCardRequested
    new_state = _apply_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.own_player_id == player_state.self_player_id
    assert isinstance(new_state.screen, GameScreen)
    assert new_state.screen.kind == "choose_card"


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

    state = _apply_server_message(CliState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.public_state == player_state.public_state
    assert state.revealed_trick == revealed


def test_uppercase_x_triggers_leave_session_and_suppresses_final_result() -> None:
    state, outbound = _apply_user_input(CliState(), "X")

    assert outbound == LeaveSession()
    assert state.should_exit is True
    assert state.suppress_final_result is True


def test_session_ended_exits_immediately() -> None:
    state = _apply_server_message(
        CliState(),
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

    state = _apply_server_message(CliState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.local_resolution is not None
    assert state.pending_presentation_events
    assert isinstance(state.pending_presentation_events[0], PresentationCardsRevealed)


def test_row_choice_committed_advances_local_resolution() -> None:
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

    state = _apply_server_message(CliState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)
    assert state.local_resolution is not None
    assert state.local_resolution.pending_row_choice is not None

    row_id = player_state.public_state.rows[0].row_id
    state = _apply_server_message(state, RowChoiceCommitted(row_id=row_id))

    assert state.local_resolution is not None
    assert state.local_resolution.pending_row_choice is None
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

    state = _apply_server_message(CliState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.presentation_events == ()
    assert state.pending_presentation_events


def test_pending_presentation_uses_enter_prompt_until_queue_is_empty() -> None:
    state = CliState(
        core_state=ClientCoreState(pending_presentation_events=(PresentationCardsRevealed(plays=()),)),
    )
    state = with_screen(state, GameScreen(kind="choose_row", player_state=_player_state_for(0)))

    assert determine_prompt(state) == "Weiter mit Enter > "


def test_enter_advances_pending_presentation_queue() -> None:
    state = CliState(
        core_state=ClientCoreState(
            pending_presentation_events=(PresentationCardsRevealed(plays=()), PresentationRowTaken("p1", "Alice", 1, (1, 2), 3, 5, (5,))),
        ),
    )
    state = with_screen(state, GameScreen(kind="waiting"))

    state, _ = _apply_user_input(state, "")

    assert len(state.presentation_events) == 1
    assert len(state.pending_presentation_events) == 1


def test_non_enter_during_pending_presentation_shows_hint() -> None:
    state = CliState(
        core_state=ClientCoreState(pending_presentation_events=(PresentationCardsRevealed(plays=()),)),
    )
    state = with_screen(state, GameScreen(kind="waiting"))

    state, _ = _apply_user_input(state, "foo")

    assert state.flash_message is not None
    assert "Enter" in state.flash_message.text


def test_choose_card_requested_clears_visible_and_pending_presentation() -> None:
    player_state = _player_state_for(0)
    state = CliState(
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
    state = CliState(core_state=ClientCoreState(own_player_id="p1", presentation_events=(PresentationCardsRevealed(plays=()),)))

    rendered = render_resolution_lines(state)
    assert rendered is not None
    assert "Lokale Auflösung" in rendered
