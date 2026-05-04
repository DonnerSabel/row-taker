from __future__ import annotations

from collections.abc import Sequence

from .models import Card, EngineRow, Row


def target_row_index(rows: Sequence[EngineRow | Row], card: Card) -> int | None:
    """Return the target row index for ``card``.

    Target row = row with the greatest last card value that is still < card.value.
    If no row fits (card is smaller than all last row cards): return None.
    """
    best_idx: int | None = None
    best_last = -1

    for i, row in enumerate(rows):
        last = row.last_value()
        if last < card.value and last > best_last:
            best_last = last
            best_idx = i

    return best_idx


def take_row(rows: list[EngineRow], row_index: int) -> tuple[int, list[Card]]:
    """Take a row and return ``(bullheads, taken_cards)``.

    The row object keeps its ``row_id`` and becomes empty.
    """
    row = rows[row_index]
    taken = list(row.cards)
    bullheads = sum(card.bullheads for card in taken)
    rows[row_index] = EngineRow(row_id=row.row_id, cards=[])
    return bullheads, taken


def place_card(
    rows: list[EngineRow],
    row_index: int,
    card: Card,
    *,
    row_capacity: int = 5,
) -> tuple[int, list[Card] | None]:
    """Place a card into the chosen row.

    If the row already contains ``row_capacity`` cards, those cards are taken and
    the played card becomes the new first card of the row.

    Return ``(bullheads_gained, taken_cards_or_none)``.
    """
    row = rows[row_index]

    if len(row.cards) >= row_capacity:
        taken_bullheads = sum(c.bullheads for c in row.cards)
        taken_cards = list(row.cards)
        rows[row_index] = EngineRow(row_id=row.row_id, cards=[card])
        return taken_bullheads, taken_cards

    row.cards.append(card)
    return 0, None
