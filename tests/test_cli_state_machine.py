from __future__ import annotations

import random

from row_taker.cli.state_machine import reduce_server_message, reduce_user_input
from row_taker.cli.state_models import CliState, GameScreen, TrickResolvedModal
from row_taker.engine.game import build_player_state, setup_game
from row_taker.engine.game.cards import Card
from row_taker.engine.game.state import DeltaPublicState
from row_taker.protocol.messages import (
    ChooseCardRequested,
    LeaveSession,
    PlayedCardView,
    SessionEnded,
    SessionEndReason,
    StateUpdated,
    TrickResolved,
    TrickRevealed,
)


def _player_state_for(index: int):
    game = setup_game(["A", "B"], rng=random.Random(123))
    player_id = game.players[index].player_id
    return build_player_state(game, player_id)



def test_choose_card_requested_enters_choose_card_screen() -> None:
    player_state = _player_state_for(0)
    state = CliState()

    new_state = reduce_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.own_player_id == player_state.self_player_id
    assert isinstance(new_state.screen, GameScreen)
    assert new_state.screen.kind == "choose_card"



def test_trick_resolved_keeps_following_choose_card_request_under_modal_until_enter() -> None:
    player_state = _player_state_for(0)
    public_state_before = player_state.public_state
    trick = TrickResolved(
        deltas=(
            DeltaPublicState(
                player_id=player_state.self_player_id,
                affected_row_id=public_state_before.rows[0].row_id,
                new_row_cards=tuple([*public_state_before.rows[0].cards, Card(104)]),
            ),
        ),
        new_round_started=False,
        game_finished=False,
    )

    state = reduce_server_message(CliState(public_state=public_state_before), trick)
    assert isinstance(state.modal, TrickResolvedModal)

    state = reduce_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert isinstance(state.modal, TrickResolvedModal)
    assert isinstance(state.screen, GameScreen)
    assert state.screen.kind == "choose_card"

    result = reduce_user_input(state, "")
    assert result.state.modal is None
    assert isinstance(result.state.screen, GameScreen)
    assert result.state.screen.kind == "choose_card"



def test_state_updated_during_trick_resolved_updates_public_state_without_closing_modal() -> None:
    player_state = _player_state_for(0)
    public_state_before = player_state.public_state
    trick = TrickResolved(deltas=(), new_round_started=False, game_finished=False)

    state = reduce_server_message(CliState(public_state=public_state_before), trick)
    assert isinstance(state.modal, TrickResolvedModal)

    new_public_state = _player_state_for(1).public_state
    state = reduce_server_message(state, StateUpdated(state=new_public_state))

    assert state.public_state == new_public_state
    assert isinstance(state.modal, TrickResolvedModal)



def test_trick_revealed_is_stored_for_following_waiting_or_choose_row_screens() -> None:
    player_state = _player_state_for(0)
    revealed = TrickRevealed(
        state=player_state.public_state,
        played_cards=(
            PlayedCardView(
                player_id=player_state.self_player_id,
                player_name=player_state.self_player_name(),
                card_value=player_state.hand[0].value,
            ),
        ),
        active_player_id=player_state.self_player_id,
        pending_card_value=player_state.hand[0].value,
    )

    state = reduce_server_message(CliState(), revealed)

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
