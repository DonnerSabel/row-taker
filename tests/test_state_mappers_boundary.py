from row_taker.engine.game.cards import Card
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PlayerState, PublicState, RulesConfig
from row_taker.engine.game.models import PublicPlayerInfo, Row, PlayerID, RowID
from row_taker.engine.game.state_mappers import (
    player_state_from_dict,
    player_state_to_dict,
    public_state_from_dict,
    public_state_to_dict,
    row_from_dict,
    row_to_dict,
)


def _public_state() -> PublicState:
    return PublicState(
        config=RulesConfig(hand_size=10, row_count=4, row_capacity=5, end_score=66),
        players=(
            PublicPlayerInfo(player_id=PlayerID("player-0"), name="Alice", score=0, hand_count=2),
            PublicPlayerInfo(player_id=PlayerID("player-1"), name="Bob", score=3, hand_count=2),
        ),
        rows=(
            Row(row_id=RowID("row-0"), cards=(Card(10), Card(11))),
            Row(row_id=RowID("row-1"), cards=(Card(20),)),
            Row(row_id=RowID("row-2"), cards=(Card(30),)),
            Row(row_id=RowID("row-3"), cards=(Card(40),)),
        ),
        round_no=1,
        trick_no=1,
        phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD),
    )


def test_row_mapper_roundtrip_preserves_public_tuple_cards() -> None:
    row = Row(row_id=RowID("row-0"), cards=(Card(10), Card(11)))

    decoded = row_from_dict(row_to_dict(row))

    assert decoded == row
    assert isinstance(decoded.cards, tuple)


def test_public_state_mapper_roundtrip_preserves_public_tuples() -> None:
    decoded = public_state_from_dict(public_state_to_dict(_public_state()))

    assert isinstance(decoded.players, tuple)
    assert isinstance(decoded.rows, tuple)
    assert isinstance(decoded.rows[0].cards, tuple)


def test_player_state_mapper_roundtrip_preserves_tuple_hand() -> None:
    player_state = PlayerState(
        public_state=_public_state(),
        self_player_id=PlayerID("player-0"),
        hand=(Card(17), Card(42)),
    )

    decoded = player_state_from_dict(player_state_to_dict(player_state))

    assert isinstance(decoded.hand, tuple)
    assert [card.value for card in decoded.hand] == [17, 42]
