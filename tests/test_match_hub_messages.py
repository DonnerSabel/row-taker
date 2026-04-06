from row_taker.engine.cards import Card
from row_taker.engine.models import PlayerID, RowID
from row_taker.engine.game import setup_game
from row_taker.engine.public_state_ops import played_card_from_delta
from row_taker.hub.match_hub import MatchHub
from row_taker.hub.messages import ChooseCardRequested, ChooseRowRequested, StateUpdated, SubmitCard, SubmitRowChoice, TrickResolved


def test_match_hub_drives_trick_via_messages() -> None:
    state = setup_game(['A', 'B'])

    # deterministischer Zustand für den Test
    state.players[0].hand = [Card(1)]
    state.players[1].hand = [Card(90)]
    for index, row in enumerate(state.rows):
        row.cards = [Card((index + 1) * 10)]

    hub = MatchHub(state=state)
    hub.start_match()

    messages = hub.drain_outbox()
    assert any(isinstance(message, StateUpdated) for message in messages)
    choose_card_messages = [message for message in messages if isinstance(message, ChooseCardRequested)]
    assert len(choose_card_messages) == 2

    hub.handle_client_message(SubmitCard(PlayerID('player-0'), 1))
    hub.handle_client_message(SubmitCard(PlayerID('player-1'), 90))

    messages = hub.drain_outbox()
    choose_row_messages = [message for message in messages if isinstance(message, ChooseRowRequested)]
    assert len(choose_row_messages) == 1
    assert choose_row_messages[0].player_id == PlayerID('player-0')

    hub.handle_client_message(SubmitRowChoice(PlayerID('player-0'), RowID('row-1')))
    messages = hub.drain_outbox()

    trick_messages = [message for message in messages if isinstance(message, TrickResolved)]
    assert len(trick_messages) == 1
    trick = trick_messages[0]
    assert [played_card_from_delta(delta).value for delta in trick.deltas] == [1, 90]
