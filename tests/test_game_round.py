from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.game import (
    all_cards_selected,
    begin_trick_resolution,
    resolve_next_delta_public_state,
    submit_choose_row,
    submit_play_card,
    trick_resolution_finished,
)
from row_taker.engine.cards import Card
from row_taker.engine.models import Player, PlayerID, Row, RowID
from row_taker.engine.phases import Phase, PhaseInfo
from row_taker.engine.state import DeltaPublicState, GameState, RulesConfig
from row_taker.engine.views import apply_delta_public_state


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


def test_resolution_in_steps_places_cards_in_ascending_order() -> None:
    state = _make_state(
        p0_hand=[42],
        p1_hand=[35],
        rows=[[10], [20], [30], [40]],
    )

    submit_play_card(state, PlayCardCommand(PlayerID("player-0"), 42))
    submit_play_card(state, PlayCardCommand(PlayerID("player-1"), 35))
    assert all_cards_selected(state)

    begin_trick_resolution(state)
    delta_1 = resolve_next_delta_public_state(state)
    delta_2 = resolve_next_delta_public_state(state)

    assert delta_1 is not None
    assert delta_2 is not None
    assert [delta_1.played_card.value, delta_2.played_card.value] == [35, 42]
    assert [card.value for card in state.rows[2].cards] == [30, 35]
    assert [card.value for card in state.rows[3].cards] == [40, 42]
    assert trick_resolution_finished(state)


def test_resolution_requires_choose_row_for_small_card() -> None:
    state = _make_state(
        p0_hand=[1],
        p1_hand=[90],
        rows=[[10], [20], [30], [40]],
    )

    submit_play_card(state, PlayCardCommand(PlayerID("player-0"), 1))
    submit_play_card(state, PlayCardCommand(PlayerID("player-1"), 90))
    begin_trick_resolution(state)

    assert resolve_next_delta_public_state(state) is None
    assert state.phase_info.phase == Phase.CHOOSE_ROW
    delta_1 = submit_choose_row(
        state,
        ChooseRowCommand(player_id=PlayerID("player-0"), row_id=RowID("row-1")),
    )
    delta_2 = resolve_next_delta_public_state(state)

    assert delta_1.affected_row_id == RowID("row-1")
    assert [card.value for card in state.rows[1].cards] == [1]
    assert state.players[0].score == Card(20).bullheads

    assert delta_2 is not None
    assert [card.value for card in state.rows[3].cards] == [40, 90]


def test_resolution_takes_full_row_on_sixth_card() -> None:
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

    submit_play_card(state, PlayCardCommand(PlayerID("player-0"), 15))
    submit_play_card(state, PlayCardCommand(PlayerID("player-1"), 90))
    begin_trick_resolution(state)

    delta_1 = resolve_next_delta_public_state(state)
    delta_2 = resolve_next_delta_public_state(state)

    assert delta_1 is not None
    assert delta_1.affected_row_id == RowID("row-0")
    assert state.players[0].score == sum(Card(v).bullheads for v in [10, 11, 12, 13, 14])
    assert [card.value for card in state.rows[0].cards] == [15]

    assert delta_2 is not None
    assert [card.value for card in state.rows[3].cards] == [40, 90]


def test_apply_delta_public_state_updates_public_scores_and_rows() -> None:
    public_before = _make_state(
        p0_hand=[15],
        p1_hand=[90],
        rows=[
            [10, 11, 12, 13, 14],
            [20],
            [30],
            [40],
        ],
    )
    from row_taker.engine.views import build_public_state

    public_state = build_public_state(public_before)
    delta = DeltaPublicState(
        player_id=PlayerID("player-0"),
        played_card=Card(15),
        affected_row_id=RowID("row-0"),
        new_row_cards=[Card(15)],
    )

    public_after = apply_delta_public_state(public_state, delta)

    assert [card.value for card in public_after.rows[0].cards] == [15]
    assert public_after.players[0].score == sum(Card(v).bullheads for v in [10, 11, 12, 13, 14])
    assert public_after.players[0].hand_count == public_state.players[0].hand_count - 1
