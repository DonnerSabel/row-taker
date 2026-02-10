from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Sequence

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
    hand: List[Card] = field(default_factory=list)
    score: int = 0


@dataclass(slots=True)
class Row:
    cards: List[Card] = field(default_factory=list)

    def last_value(self) -> int:
        return self.cards[-1].value

    def points(self) -> int:
        return sum(c.points for c in self.cards)


@dataclass(slots=True)
class GameState:
    players: List[Player]
    rows: List[Row]
    deck: List[Card]
    hand_size: int = 10
    round_no: int = 1


# Callback-Typ: Wenn eine Karte kleiner als alle Reihen ist,
# muss der Spieler eine Reihe zum Nehmen auswählen.
ChooseRowFn = Callable[[GameState, int, Card], int]
"""(state, player_index, played_card) -> row_index"""
