from __future__ import annotations

import random

from row_taker.cli.state_machine import reduce_server_message, reduce_user_input
from row_taker.cli.state_models import CliState, GameScreen
from row_taker.engine.game import build_player_state, setup_game
from row_taker.protocol.messages import (
    CardsRevealed,
    LeaveSession,
    PlayedCardView,
    SessionEnded,
    SessionEndReason,
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
        played_cards=(
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
