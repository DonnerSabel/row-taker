from __future__ import annotations

import random

from row_taker.cli.render import determine_prompt, render_resolution_lines
from row_taker.cli.state_machine import reduce_server_message, reduce_user_input
from row_taker.cli.state_models import CliState, GameScreen
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


def _player_state_for(index: int):
    game = setup_game(["A", "B"], rng=random.Random(123))
    player_id = game.players[index].player_id
    return build_player_state(game, player_id)


def test_state_updated_sets_public_state() -> None:
    player_state = _player_state_for(0)
    state = CliState()

    new_state = reduce_server_message(state, StateUpdated(state=player_state.public_state))
    assert new_state.public_state == player_state.public_state


def test_choose_card_requested_enters_choose_card_screen() -> None:
    player_state = _player_state_for(0)
    state = CliState()

    from row_taker.protocol.messages import ChooseCardRequested
    new_state = reduce_server_message(
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

    state = reduce_server_message(CliState(public_state=player_state.public_state), revealed)

    assert state.public_state == player_state.public_state
    assert state.revealed_trick == revealed


def test_uppercase_x_triggers_leave_session_and_suppresses_final_result() -> None:
    result = reduce_user_input(CliState(), "X")

    assert result.outbound_message == LeaveSession()
    assert result.state.should_exit is True
    assert result.state.suppress_final_result is True


def test_session_ended_exits_immediately() -> None:
    state = reduce_server_message(
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

    state = reduce_server_message(CliState(public_state=player_state.public_state), revealed)

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

    state = reduce_server_message(CliState(public_state=player_state.public_state), revealed)
    assert state.local_resolution is not None
    assert state.local_resolution.pending_row_choice is not None

    row_id = player_state.public_state.rows[0].row_id
    state = reduce_server_message(state, RowChoiceCommitted(row_id=row_id))

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

    state = reduce_server_message(CliState(public_state=player_state.public_state), revealed)

    assert state.presentation_events == ()
    assert state.pending_presentation_events


def test_pending_presentation_uses_enter_prompt_until_queue_is_empty() -> None:
    state = CliState(
        screen=GameScreen(kind="choose_row", player_state=_player_state_for(0)),
        pending_presentation_events=(PresentationCardsRevealed(plays=()),),
    )

    assert determine_prompt(state) == "Weiter mit Enter > "


def test_enter_advances_pending_presentation_queue() -> None:
    state = CliState(
        screen=GameScreen(kind="waiting"),
        pending_presentation_events=(PresentationCardsRevealed(plays=()), PresentationRowTaken("p1", "Alice", 1, (1, 2), 3, 5, (5,))),
    )

    result = reduce_user_input(state, "")

    assert len(result.state.presentation_events) == 1
    assert len(result.state.pending_presentation_events) == 1


def test_non_enter_during_pending_presentation_shows_hint() -> None:
    state = CliState(
        screen=GameScreen(kind="waiting"),
        pending_presentation_events=(PresentationCardsRevealed(plays=()),),
    )

    result = reduce_user_input(state, "foo")

    assert result.state.flash_message is not None
    assert "Enter" in result.state.flash_message.text


def test_choose_card_requested_clears_visible_and_pending_presentation() -> None:
    player_state = _player_state_for(0)
    state = CliState(
        public_state=player_state.public_state,
        presentation_events=(PresentationCardsRevealed(plays=()),),
        pending_presentation_events=(PresentationCardsRevealed(plays=()),),
    )

    from row_taker.protocol.messages import ChooseCardRequested
    new_state = reduce_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.presentation_events == ()
    assert new_state.pending_presentation_events == ()


def test_render_resolution_lines_renders_from_presentation_events() -> None:
    state = CliState(
        own_player_id="p1",
        presentation_events=(PresentationCardsRevealed(plays=()),),
    )

    rendered = render_resolution_lines(state)
    assert rendered is not None
    assert "Lokale Auflösung" in rendered
