from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .scoring import bullheads


@dataclass(frozen=True, slots=True)
class Card:
    value: int

    @property
    def points(self) -> int:
        return bullheads(self.value)


@dataclass(slots=True)
class Player:
    name: str
    hand: list[Card] = field(default_factory=list)
    score: int = 0


@dataclass(slots=True)
class Row:
    cards: list[Card] = field(default_factory=list)

    def last_value(self) -> int:
        return self.cards[-1].value

    def points(self) -> int:
        return sum(c.points for c in self.cards)


@dataclass(slots=True)
class GameState:
    players: list[Player]
    rows: list[Row]
    deck: list[Card]
    hand_size: int = 10
    round_no: int = 1


# Callback-Typ: Wenn eine Karte kleiner als alle Reihen ist,
# muss der Spieler eine Reihe zum Nehmen auswählen.
ChooseRowFn = Callable[[GameState, int, Card], int]
"""(state, player_index, played_card) -> row_index"""
