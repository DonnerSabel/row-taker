from row_taker.engine.game import (
    all_cards_selected,
    begin_trick_resolution,
    has_pending_resolution_step,
    has_pending_row_choice,
    resolve_next_trick_step,
    submit_choose_row,
    submit_play_card,
)
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import EngineRow, Player, PlayerID, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.game.public_state_ops import apply_resolution_step
from row_taker.engine.game.state import GameState, RulesConfig


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
            EngineRow(row_id=RowID(f"row-{i}"), cards=[Card(v) for v in row_cards])
            for i, row_cards in enumerate(rows)
        ],
        deck=[],
        round_no=1,
        trick_no=1,
        phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD),
    )


def test_resolution_produces_steps_in_ascending_order() -> None:
    state = _make_state(
        p0_hand=[42],
        p1_hand=[35],
        rows=[[10], [20], [30], [40]],
    )

    submit_play_card(state, PlayerID("player-0"), 42)
    submit_play_card(state, PlayerID("player-1"), 35)
    assert all_cards_selected(state) is True

    begin_trick_resolution(state)
    assert has_pending_resolution_step(state) is True

    first = resolve_next_trick_step(state)
    second = resolve_next_trick_step(state)

    assert first is not None
    assert second is not None
    assert [first.played_card.value, second.played_card.value] == [35, 42]


def test_choose_row_step_can_be_applied_to_public_state() -> None:
    state = _make_state(
        p0_hand=[1],
        p1_hand=[90],
        rows=[[10], [20], [30], [40]],
    )

    submit_play_card(state, PlayerID("player-0"), 1)
    submit_play_card(state, PlayerID("player-1"), 90)
    public_before = __import__(
        "row_taker.engine.game.views", fromlist=["build_public_state"]
    ).build_public_state(state)

    begin_trick_resolution(state)
    prompt = resolve_next_trick_step(state)
    assert prompt is not None
    assert has_pending_row_choice(state) is True

    choose_step = submit_choose_row(state, PlayerID("player-0"), RowID("row-1"))
    updated = apply_resolution_step(public_before, choose_step)

    assert choose_step.action == StepAction.TOOK_ROW_SMALL
    assert choose_step.points_gained == Card(20).bullheads
    assert [card.value for card in updated.rows[1].cards] == [1]
    assert updated.players[0].score == Card(20).bullheads
