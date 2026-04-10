from __future__ import annotations

import random

from row_taker.cli.state_machine import reduce_server_message, reduce_user_input
from row_taker.cli.state_models import CliState, GameStateChooseCard, GameStateTrickResolved
from row_taker.engine.game import build_player_state, setup_game
from row_taker.engine.game.cards import Card
from row_taker.engine.game.state import DeltaPublicState
from row_taker.protocol.messages import ChooseCardRequested, StateUpdated, TrickResolved


def _player_state_for(index: int):
    game = setup_game(["A", "B"], rng=random.Random(123))
    player_id = game.players[index].player_id
    return build_player_state(game, player_id)



def test_choose_card_requested_enters_choose_card_mode() -> None:
    player_state = _player_state_for(0)
    state = CliState()

    new_state = reduce_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.own_player_id == player_state.self_player_id
    assert isinstance(new_state.mode, GameStateChooseCard)



def test_trick_resolved_buffers_following_choose_card_request_until_enter() -> None:
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
    assert isinstance(state.mode, GameStateTrickResolved)

    state = reduce_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert isinstance(state.mode, GameStateTrickResolved)
    assert isinstance(state.pending_next_state, GameStateChooseCard)

    result = reduce_user_input(state, "")
    assert isinstance(result.state.mode, GameStateChooseCard)
    assert result.state.pending_next_state is None



def test_state_updated_during_trick_resolved_updates_public_state_without_leaving_mode() -> None:
    player_state = _player_state_for(0)
    public_state_before = player_state.public_state
    trick = TrickResolved(deltas=(), new_round_started=False, game_finished=False)

    state = reduce_server_message(CliState(public_state=public_state_before), trick)
    assert isinstance(state.mode, GameStateTrickResolved)

    new_public_state = _player_state_for(1).public_state
    state = reduce_server_message(state, StateUpdated(state=new_public_state))

    assert state.public_state == new_public_state
    assert isinstance(state.mode, GameStateTrickResolved)
