from __future__ import annotations


def bullheads(card_value: int) -> int:
    """Berechnet die Strafpunkte (Bullheads) für einen Kartenwert.

    Regeln (Kurzfassung):
    - 55 → 7
    - Vielfache von 11 → 5
    - Vielfache von 10 → 3
    - Vielfache von 5 → 2
    - sonst → 1
    """
    if not (1 <= card_value <= 104):
        raise ValueError(f"card_value out of range: {card_value}")

    if card_value == 55:
        return 7
    if card_value % 11 == 0:
        return 5
    if card_value % 10 == 0:
        return 3
    if card_value % 5 == 0:
        return 2
    return 1
