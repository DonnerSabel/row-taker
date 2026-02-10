import random

from row_taker.engine.game import StepResult, resolve_round, setup_game
from row_taker.engine.state import Card, GameState


def test_resolve_round_small_card_forces_take() -> None:
    rng = random.Random(1)
    state: GameState = setup_game(["A", "B"], rng=rng, hand_size=1)

    # Wir konstruieren einen Zustand: Reihen enden hoch, Spieler A spielt sehr klein.
    state.rows[0].cards = [Card(50)]
    state.rows[1].cards = [Card(60)]
    state.rows[2].cards = [Card(70)]
    state.rows[3].cards = [Card(80)]

    # Hände manuell setzen
    state.players[0].hand = [Card(1)]
    state.players[1].hand = [Card(90)]

    def choose_row(_state: GameState, player_index: int, played_card: Card) -> int:
        assert player_index == 0
        assert played_card.value == 1
        return 2  # Spieler nimmt Reihe 2

    results: list[StepResult] = resolve_round(state, {0: Card(1), 1: Card(90)}, choose_row)
    assert results[0].action == "took_row_small"
    assert state.rows[2].cards[0].value == 1


def test_resolve_round_order_is_ascending() -> None:
    rng = random.Random(2)
    state: GameState = setup_game(["A", "B", "C"], rng=rng, hand_size=1)
    # Hände setzen: absichtlich unsortiert
    state.players[0].hand = [Card(30)]
    state.players[1].hand = [Card(10)]
    state.players[2].hand = [Card(20)]

    def choose_row(_state: GameState, _pi: int, _card: Card) -> int:
        return 0

    results: list[StepResult] = resolve_round(state, {0: Card(30), 1: Card(10), 2: Card(20)}, choose_row)
    values: list[int] = [r.card.value for r in results]
    assert values == [10, 20, 30]
