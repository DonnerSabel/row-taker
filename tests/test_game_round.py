from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.game import resolve_round
from row_taker.engine.cards import Card
from row_taker.engine.models import Player, PlayerID, Row, RowID
from row_taker.engine.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.state import GameState, RulesConfig


def _make_state(*, p0_hand: list[int], p1_hand: list[int], rows: list[list[int]]) -> GameState:
    return GameState(
        config=RulesConfig(hand_size=10, row_count=4, row_capacity=5, end_score=66),
        players=[
            Player(
                player_id=PlayerID("player-0"),
                name="A",
                hand=[Card(v) for v in p0_hand],
                score=0,
            ),
            Player(
                player_id=PlayerID("player-1"),
                name="B",
                hand=[Card(v) for v in p1_hand],
                score=0,
            ),
        ],
        rows=[
            Row(row_id=RowID(f"row-{i}"), cards=[Card(v) for v in row_cards])
            for i, row_cards in enumerate(rows)
        ],
        deck=[],
        round_no=1,
        trick_no=1,
        phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD),
    )


def test_resolve_round_places_cards_in_ascending_order() -> None:
    state = _make_state(
        p0_hand=[42],
        p1_hand=[35],
        rows=[[10], [20], [30], [40]],
    )

    results = resolve_round(
        state,
        {
            PlayerID("player-0"): PlayCardCommand(PlayerID("player-0"), 42),
            PlayerID("player-1"): PlayCardCommand(PlayerID("player-1"), 35),
        },
        lambda _state, _player_id, _card: ChooseRowCommand(PlayerID("player-0"), RowID("row-0")),
    )

    assert [result.card.value for result in results] == [35, 42]
    assert [card.value for card in state.rows[2].cards] == [30, 35]
    assert [card.value for card in state.rows[3].cards] == [40, 42]
    assert state.phase_info.phase == Phase.ROUND_SCORING


def test_resolve_round_requires_choose_row_for_small_card() -> None:
    state = _make_state(
        p0_hand=[1],
        p1_hand=[90],
        rows=[[10], [20], [30], [40]],
    )

    called: list[tuple[str, int]] = []

    def choose_row(_state: GameState, player_id: PlayerID, played_card: Card) -> ChooseRowCommand:
        called.append((str(player_id), played_card.value))
        return ChooseRowCommand(player_id=player_id, row_id=RowID("row-1"))

    results = resolve_round(
        state,
        {
            PlayerID("player-0"): PlayCardCommand(PlayerID("player-0"), 1),
            PlayerID("player-1"): PlayCardCommand(PlayerID("player-1"), 90),
        },
        choose_row,
    )

    assert called == [("player-0", 1)]
    assert results[0].action == StepAction.TOOK_ROW_SMALL
    assert results[0].row_id == RowID("row-1")
    assert [card.value for card in state.rows[1].cards] == [1]
    assert state.players[0].score == Card(20).bullheads

    assert results[1].action == StepAction.PLACED
    assert [card.value for card in state.rows[3].cards] == [40, 90]


def test_resolve_round_takes_full_row_on_sixth_card() -> None:
    state = _make_state(
        p0_hand=[15],
        p1_hand=[90],
        rows=[
            [10, 11, 12, 13, 14],
            [20],
            [30],
            [40],
        ],
    )

    results = resolve_round(
        state,
        {
            PlayerID("player-0"): PlayCardCommand(PlayerID("player-0"), 15),
            PlayerID("player-1"): PlayCardCommand(PlayerID("player-1"), 90),
        },
        lambda _state, player_id, _card: ChooseRowCommand(player_id=player_id, row_id=RowID("row-0")),
    )

    assert results[0].action == StepAction.TOOK_ROW_OVERFLOW
    assert results[0].row_id == RowID("row-0")
    assert state.players[0].score == sum(Card(v).bullheads for v in [10, 11, 12, 13, 14])
    assert [card.value for card in state.rows[0].cards] == [15]

    assert results[1].action == StepAction.PLACED
    assert [card.value for card in state.rows[3].cards] == [40, 90]


def test_resolve_round_rejects_incomplete_selection_map() -> None:
    state = _make_state(
        p0_hand=[15],
        p1_hand=[90],
        rows=[[10], [20], [30], [40]],
    )

    try:
        resolve_round(
            state,
            {
                PlayerID("player-0"): PlayCardCommand(PlayerID("player-0"), 15),
            },
            lambda _state, player_id, _card: ChooseRowCommand(player_id=player_id, row_id=RowID("row-0")),
        )
    except ValueError as exc:
        assert "one card for every player_id" in str(exc)
    else:
        raise AssertionError("resolve_round should reject incomplete selection maps")
