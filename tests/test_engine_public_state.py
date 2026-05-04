from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.game.state import (
    EnginePublicState,
    PublicState,
    RulesConfig,
    TrickResolutionStep,
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
        phase_info=PhaseInfo(phase=Phase.REVEAL_AND_RESOLVE),
    )


def test_from_public_state_creates_mutable_engine_copy() -> None:
    public_state = _public_state()

    engine_state = EnginePublicState.from_public_state(public_state)
    engine_state.rows[0].cards.append(Card(12))

    assert [card.value for card in engine_state.rows[0].cards] == [10, 11, 12]
    assert [card.value for card in public_state.rows[0].cards] == [10, 11]


def test_to_public_state_returns_immutable_public_types() -> None:
    engine_state = EnginePublicState.from_public_state(_public_state())
    engine_state.rows[1].cards = [Card(99)]

    public_state = engine_state.to_public_state()

    assert isinstance(public_state.rows, tuple)
    assert isinstance(public_state.rows[1].cards, tuple)
    assert [card.value for card in public_state.rows[1].cards] == [99]


def test_apply_resolution_step_updates_row_and_player() -> None:
    engine_state = EnginePublicState.from_public_state(_public_state())
    step = TrickResolutionStep(
        action=StepAction.TOOK_ROW_SMALL,
        player_id=PlayerID("player-0"),
        affected_row_id=RowID("row-1"),
        played_card=Card(5),
        taken_cards=(Card(20),),
        points_gained=Card(20).bullheads,
        new_row_cards=(Card(5),),
    )

    engine_state.apply_resolution_step(step)

    assert [card.value for card in engine_state.rows[1].cards] == [5]
    assert engine_state.get_player_by_id(PlayerID("player-0")).score == Card(20).bullheads
    assert engine_state.get_player_by_id(PlayerID("player-0")).hand_count == 1
