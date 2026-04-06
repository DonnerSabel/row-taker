from row_taker.engine.cards import Card
from row_taker.engine.models import PlayerID, RowID
from row_taker.engine.phases import Phase, PhaseInfo
from row_taker.engine.state import DeltaPublicState, PlayerState, PublicState, RulesConfig
from row_taker.engine.models import PublicPlayerInfo, Row
from row_taker.hub.message_mappers import client_message_from_dict, client_message_to_dict, hub_message_from_dict, hub_message_to_dict
from row_taker.hub.messages import ChooseCardRequested, StateUpdated, SubmitCard, SubmitRowChoice, TrickResolved


def _public_state() -> PublicState:
    return PublicState(
        config=RulesConfig(),
        players=[PublicPlayerInfo(player_id=PlayerID('player-0'), name='A', score=3, hand_count=7)],
        rows=[Row(row_id=RowID('row-0'), cards=[Card(10)])],
        round_no=2,
        trick_no=5,
        phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD, message='Choose one card.'),
    )


def test_client_message_mappers_roundtrip() -> None:
    submit_card = SubmitCard(player_id=PlayerID('player-0'), card_value=42)
    assert client_message_from_dict(client_message_to_dict(submit_card)) == submit_card

    submit_row = SubmitRowChoice(player_id=PlayerID('player-0'), row_id=RowID('row-2'))
    assert client_message_from_dict(client_message_to_dict(submit_row)) == submit_row


def test_hub_message_mappers_roundtrip() -> None:
    public_state = _public_state()
    player_state = PlayerState(public_state=public_state, self_player_id=PlayerID('player-0'), hand=[Card(42)])
    delta = DeltaPublicState(player_id=PlayerID('player-0'), affected_row_id=RowID('row-0'), new_row_cards=(Card(10), Card(42)))

    state_updated = StateUpdated(state=public_state)
    assert hub_message_from_dict(hub_message_to_dict(state_updated)) == state_updated

    choose_card = ChooseCardRequested(player_id=PlayerID('player-0'), state=player_state)
    assert hub_message_from_dict(hub_message_to_dict(choose_card)) == choose_card

    trick_resolved = TrickResolved(deltas=(delta,), new_round_started=False, game_finished=False)
    assert hub_message_from_dict(hub_message_to_dict(trick_resolved)) == trick_resolved
