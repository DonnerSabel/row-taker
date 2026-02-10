from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .state import Card, Row


def target_row_index(rows: Sequence[Row], card: Card) -> Optional[int]:
    """Gibt die Zielreihe für `card` zurück.

    Zielreihe = Reihe mit der größten letzten Karte, die noch < card.value ist.
    Falls keine Reihe passt (card ist kleiner als alle letzten Karten): None.
    """
    best_idx: Optional[int] = None
    best_last = -1

    for i, row in enumerate(rows):
        last = row.last_value()
        if last < card.value and last > best_last:
            best_last = last
            best_idx = i

    return best_idx


def take_row(rows: List[Row], row_index: int) -> Tuple[int, List[Card]]:
    """Nimmt eine Reihe: liefert (punkte, genommene_karten)."""
    row = rows[row_index]
    taken = list(row.cards)
    points = sum(c.points for c in taken)
    rows[row_index] = Row(cards=[])
    return points, taken


def place_card(rows: List[Row], row_index: int, card: Card) -> Tuple[int, Optional[List[Card]]]:
    """Legt eine Karte in die Zielreihe.

    Wenn die Reihe dadurch 6 Karten hätte, werden die bisherigen 5 Karten genommen.
    Rückgabe: (punkte, ggf. genommene_karten oder None).
    """
    row = rows[row_index]

    # Wenn schon 5 Karten liegen und wir die 6. hinzufügen würden:
    if len(row.cards) >= 5:
        taken_points = sum(c.points for c in row.cards)
        taken_cards = list(row.cards)
        rows[row_index] = Row(cards=[card])
        return taken_points, taken_cards

    row.cards.append(card)
    return 0, None
