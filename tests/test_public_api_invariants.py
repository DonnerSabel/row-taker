from row_taker.engine.game import (
    EnginePublicState,
    EngineRow,
    GameState,
    Player,
    PlayerID,
    PublicState,
    Row,
    RowID,
    RulesConfig,
    apply_resolution_step,
    build_player_state,
    build_public_state,
)
from row_taker.engine.game.cards import Card
from row_taker.engine.game.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.game.state import TrickResolutionStep


def _game_state() -> GameState:
    return GameState(
        config=RulesConfig(hand_size=10, row_count=4, row_capacity=5, end_score=66),
        players=[
            Player(
                player_id=PlayerID("player-0"),
                name="Alice",
                hand=[Card(11), Card(17)],
                score=0,
            ),
            Player(
                player_id=PlayerID("player-1"),
                name="Bob",
                hand=[Card(42), Card(55)],
                score=3,
            ),
        ],
        rows=[
            EngineRow(row_id=RowID("row-0"), cards=[Card(10), Card(12)]),
            EngineRow(row_id=RowID("row-1"), cards=[Card(20)]),
            EngineRow(row_id=RowID("row-2"), cards=[Card(30)]),
            EngineRow(row_id=RowID("row-3"), cards=[Card(40)]),
        ],
        deck=[],
        round_no=1,
        trick_no=1,
        phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD),
    )


def test_engine_game_package_exports_engine_types() -> None:
    public_state = build_public_state(_game_state())
    engine_state = EnginePublicState.from_public_state(public_state)

    assert isinstance(engine_state, EnginePublicState)
    assert isinstance(engine_state.rows[0], EngineRow)


def test_build_public_state_returns_tuple_based_public_types() -> None:
    public_state = build_public_state(_game_state())

    assert isinstance(public_state, PublicState)
    assert isinstance(public_state.players, tuple)
    assert isinstance(public_state.rows, tuple)
    assert isinstance(public_state.rows[0], Row)
    assert isinstance(public_state.rows[0].cards, tuple)


def test_build_player_state_returns_tuple_hand() -> None:
    player_state = build_player_state(_game_state(), PlayerID("player-0"))

    assert isinstance(player_state.hand, tuple)
    assert [card.value for card in player_state.hand] == [11, 17]


def test_apply_resolution_step_returns_fully_immutable_public_state() -> None:
    public_state = build_public_state(_game_state())
    step = TrickResolutionStep(
        action=StepAction.TOOK_ROW_SMALL,
        player_id=PlayerID("player-0"),
        affected_row_id=RowID("row-1"),
        played_card=Card(5),
        taken_cards=(Card(20),),
        points_gained=Card(20).bullheads,
        new_row_cards=(Card(5),),
    )

    updated = apply_resolution_step(public_state, step)

    assert isinstance(updated, PublicState)
    assert isinstance(updated.players, tuple)
    assert isinstance(updated.rows, tuple)
    assert isinstance(updated.rows[1], Row)
    assert isinstance(updated.rows[1].cards, tuple)
    assert [card.value for card in updated.rows[1].cards] == [5]
    assert updated.players[0].score == Card(20).bullheads
    assert updated.players[0].hand_count == 1
