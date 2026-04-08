from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import Row, RowID
from row_taker.engine.game.rules import place_card, target_row_index


def test_target_row_index_picks_best_lower_row() -> None:
    rows = [
        Row(row_id=RowID("row-0"), cards=[Card(10)]),
        Row(row_id=RowID("row-1"), cards=[Card(20)]),
        Row(row_id=RowID("row-2"), cards=[Card(30)]),
        Row(row_id=RowID("row-3"), cards=[Card(40)]),
    ]

    assert target_row_index(rows, Card(25)) == 1
    assert target_row_index(rows, Card(41)) == 3
    assert target_row_index(rows, Card(5)) is None


def test_place_card_appends_when_row_not_full() -> None:
    rows = [
        Row(row_id=RowID("row-0"), cards=[Card(10), Card(12)]),
    ]

    points, taken = place_card(rows, 0, Card(15), row_capacity=5)

    assert points == 0
    assert taken is None
    assert [card.value for card in rows[0].cards] == [10, 12, 15]


def test_place_card_takes_row_when_row_is_full() -> None:
    rows = [
        Row(
            row_id=RowID("row-0"),
            cards=[Card(10), Card(11), Card(12), Card(13), Card(14)],
        ),
    ]

    points, taken = place_card(rows, 0, Card(15), row_capacity=5)

    assert points == sum(card.bullheads for card in [Card(10), Card(11), Card(12), Card(13), Card(14)])
    assert taken is not None
    assert [card.value for card in taken] == [10, 11, 12, 13, 14]
    assert [card.value for card in rows[0].cards] == [15]
    assert rows[0].row_id == RowID("row-0")
