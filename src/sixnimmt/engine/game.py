from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .rules import place_card, take_row, target_row_index
from .state import Card, ChooseRowFn, GameState, Player, Row


def make_deck() -> List[Card]:
    return [Card(v) for v in range(1, 105)]


def setup_game(
    player_names: Sequence[str],
    *,
    rng: Optional[random.Random] = None,
    hand_size: int = 10,
) -> GameState:
    """Erstellt einen neuen Spielzustand und teilt aus (erste Runde)."""
    if rng is None:
        rng = random.Random()

    if not (2 <= len(player_names) <= 6):
        raise ValueError("player count must be 2..6")

    deck = make_deck()
    rng.shuffle(deck)

    players = [Player(name=n) for n in player_names]
    rows = [Row([]) for _ in range(4)]

    state = GameState(players=players, rows=rows, deck=deck, hand_size=hand_size, round_no=1)
    _deal_new_round(state)
    return state


def _deal_new_round(state: GameState) -> None:
    """Teilt eine neue Runde aus: 4 Startkarten in Reihen + Handkarten."""
    # Reihen initialisieren
    for row in state.rows:
        row.cards.clear()

    for i in range(4):
        state.rows[i].cards.append(state.deck.pop())

    # Hände
    for p in state.players:
        p.hand.clear()
        for _ in range(state.hand_size):
            p.hand.append(state.deck.pop())
        p.hand.sort(key=lambda c: c.value)


@dataclass(slots=True)
class StepResult:
    player_index: int
    card: Card
    action: str  # "placed" | "took_row_small" | "took_row_overflow"
    row_index: int
    points_gained: int


def resolve_round(
    state: GameState,
    selections: Dict[int, Card],
    choose_row: ChooseRowFn,
) -> List[StepResult]:
    """Löst eine Runde auf.

    `selections`: mapping player_index -> chosen Card (muss in deren Hand gewesen sein).
    Reihenfolge: Kartenwert aufsteigend.
    """
    if set(selections.keys()) != set(range(len(state.players))):
        raise ValueError("selections must contain one card for every player index")

    # Validierung + Karte aus Hand entfernen
    for pi, card in selections.items():
        hand = state.players[pi].hand
        try:
            idx = next(i for i, c in enumerate(hand) if c.value == card.value)
        except StopIteration as e:
            raise ValueError(f"player {pi} does not have card {card.value}") from e
        hand.pop(idx)

    order = sorted(selections.items(), key=lambda kv: kv[1].value)
    results: List[StepResult] = []

    for player_index, card in order:
        idx = target_row_index(state.rows, card)

        if idx is None:
            # Karte ist kleiner als alle letzten Karten → Spieler wählt eine Reihe, nimmt sie, Karte startet dort.
            chosen = choose_row(state, player_index, card)
            if not (0 <= chosen < len(state.rows)):
                raise ValueError("choose_row returned invalid row index")

            points, _taken = take_row(state.rows, chosen)
            state.players[player_index].score += points
            # Karte startet die Reihe
            state.rows[chosen].cards = [card]

            results.append(
                StepResult(
                    player_index=player_index,
                    card=card,
                    action="took_row_small",
                    row_index=chosen,
                    points_gained=points,
                )
            )
            continue

        points, taken = place_card(state.rows, idx, card)
        if taken is not None:
            state.players[player_index].score += points
            action = "took_row_overflow"
        else:
            action = "placed"

        results.append(
            StepResult(
                player_index=player_index,
                card=card,
                action=action,
                row_index=idx,
                points_gained=points,
            )
        )

    return results


def start_next_round_if_needed(state: GameState, *, rng: Optional[random.Random] = None) -> bool:
    """Wenn alle Hände leer sind, wird eine neue Runde ausgeteilt.

    Rückgabe: True wenn neue Runde gestartet wurde.
    """
    if any(p.hand for p in state.players):
        return False

    # Falls das Deck zu klein ist, könnte man hier enden – für Unterrichtsversion reicht:
    if len(state.deck) < 4 + len(state.players) * state.hand_size:
        return False

    state.round_no += 1
    _deal_new_round(state)
    return True
