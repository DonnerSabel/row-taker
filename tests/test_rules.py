from row_taker.engine.rules import place_card, target_row_index
from row_taker.engine.state import Card, Row


def test_target_row_index():
    rows = [
        Row([Card(10)]),
        Row([Card(20)]),
        Row([Card(30)]),
        Row([Card(40)]),
    ]
    assert target_row_index(rows, Card(25)) == 1  # 20 ist beste < 25
    assert target_row_index(rows, Card(41)) == 3
    assert target_row_index(rows, Card(1)) is None


def test_place_card_overflow_takes_row():
    row = Row([Card(1), Card(2), Card(3), Card(4), Card(5)])  # 5 Karten
    rows = [row]
    points, taken = place_card(rows, 0, Card(6))
    assert taken is not None
    assert rows[0].cards[0].value == 6
    assert points > 0
