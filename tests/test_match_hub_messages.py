from row_taker.engine.cards import Card
from row_taker.engine.game import setup_game
from row_taker.engine.models import PlayerID, RowID
from row_taker.hub.match_hub import MatchHub, WaitingState
from row_taker.hub.messages import ChooseCardRequested, ChooseRowRequested, StateUpdated, SubmitCard, SubmitRowChoice, TrickResolved


def _messages_of_type(messages: list[object], cls: type[object]) -> list[object]:
    return [message for message in messages if isinstance(message, cls)]


def test_start_trick_emits_state_update_and_card_requests() -> None:
    state = setup_game(['A', 'B'])
    hub = MatchHub(state=state)

    hub.start_trick()
    messages = hub.drain_outbox()

    assert len(_messages_of_type(messages, StateUpdated)) == 1
    card_requests = _messages_of_type(messages, ChooseCardRequested)
    assert len(card_requests) == 2
    assert hub.waiting_state == WaitingState.WAITING_FOR_CARDS


def test_trick_resolves_after_all_cards_are_submitted() -> None:
    state = setup_game(['A', 'B'])
    state.players[0].hand = [Card(11)]
    state.players[1].hand = [Card(12)]
    for row, value in zip(state.rows, [5, 20, 30, 40], strict=True):
        row.cards = [Card(value)]

    hub = MatchHub(state=state)
    hub.start_trick()
    hub.drain_outbox()

    hub.handle_client_message(SubmitCard(player_id=PlayerID('player-0'), card_value=11))
    assert hub.drain_outbox() == []

    hub.handle_client_message(SubmitCard(player_id=PlayerID('player-1'), card_value=12))
    messages = hub.drain_outbox()

    assert len(messages) == 1
    result = messages[0]
    assert isinstance(result, TrickResolved)
    assert result.resolution[0].card.value == 11
    assert result.resolution[1].card.value == 12
    assert hub.waiting_state == WaitingState.TRICK_FINISHED


def test_hub_blocks_for_row_choice_when_needed() -> None:
    state = setup_game(['A', 'B'])
    state.players[0].hand = [Card(1)]
    state.players[1].hand = [Card(90)]
    for row, value in zip(state.rows, [10, 20, 30, 40], strict=True):
        row.cards = [Card(value)]

    hub = MatchHub(state=state)
    hub.start_trick()
    hub.drain_outbox()

    hub.handle_client_message(SubmitCard(player_id=PlayerID('player-0'), card_value=1))
    hub.handle_client_message(SubmitCard(player_id=PlayerID('player-1'), card_value=90))
    messages = hub.drain_outbox()

    assert len(messages) == 1
    request = messages[0]
    assert isinstance(request, ChooseRowRequested)
    assert request.player_id == PlayerID('player-0')
    assert hub.waiting_state == WaitingState.WAITING_FOR_ROW_CHOICE

    hub.handle_client_message(SubmitRowChoice(player_id=PlayerID('player-0'), row_id=RowID('row-1')))
    messages = hub.drain_outbox()

    assert len(messages) == 1
    result = messages[0]
    assert isinstance(result, TrickResolved)
    assert result.resolution[0].player_id == PlayerID('player-0')
    assert result.resolution[0].row_id == RowID('row-1')
    assert hub.waiting_state == WaitingState.TRICK_FINISHED
