from dataclasses import dataclass, field
from typing import NewType

from .scoring import bullheads


PlayerID = NewType("PlayerID", str)
RowID = NewType("RowID", str)


@dataclass(frozen=True, slots=True)
class Card:
    value: int

    @property
    def points(self) -> int:
        return bullheads(self.value)


@dataclass(slots=True)
class Row:
    row_id: RowID
    cards: list[Card] = field(default_factory=list)

    def last_value(self) -> int:
        return self.cards[-1].value

    def points(self) -> int:
        return sum(card.points for card in self.cards)


@dataclass(slots=True)
class Player:
    player_id: PlayerID
    name: str
    hand: list[Card] = field(default_factory=list)
    score: int = 0


@dataclass(frozen=True, slots=True)
class PublicPlayerInfo:
    player_id: PlayerID
    name: str
    score: int
    hand_count: int
