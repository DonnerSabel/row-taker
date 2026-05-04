from row_taker.engine.game import setup_game
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.hub.match_hub import MatchHub
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    RowChoiceCommitted,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)


def test_match_hub_drives_trick_via_messages() -> None:
    state = setup_game(["A", "B"])

    state.players[0].hand = [Card(1)]
    state.players[1].hand = [Card(90)]
    for index, row in enumerate(state.rows):
        row.cards = [Card((index + 1) * 10)]

    hub = MatchHub(state=state)
    hub.start_match()

    messages = hub.drain_outbox()
    assert any(isinstance(message, StateUpdated) for message in messages)
    choose_card_messages = [
        message for message in messages if isinstance(message, ChooseCardRequested)
    ]
    assert len(choose_card_messages) == 2

    hub.handle_client_message(PlayerID("player-0"), SubmitCard(1))
    hub.handle_client_message(PlayerID("player-1"), SubmitCard(90))

    messages = hub.drain_outbox()
    reveal_messages = [message for message in messages if isinstance(message, CardsRevealed)]
    assert len(reveal_messages) == 1
    reveal = reveal_messages[0]
    assert [card.card_value for card in reveal.plays] == [1, 90]

    choose_row_messages = [
        message for message in messages if isinstance(message, ChooseRowRequested)
    ]
    assert len(choose_row_messages) == 1
    assert choose_row_messages[0].player_id == PlayerID("player-0")

    hub.handle_client_message(PlayerID("player-0"), SubmitRowChoice(RowID("row-1")))
    messages = hub.drain_outbox()

    assert any(isinstance(message, RowChoiceCommitted) for message in messages)
    assert any(isinstance(message, StateUpdated) for message in messages)
