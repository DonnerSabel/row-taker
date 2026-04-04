from __future__ import annotations

import random
from dataclasses import dataclass, field

from .scoring import bullheads


@dataclass(frozen=True, slots=True)
class Card:
    value: int

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def validate_value(cls, value: int) -> None:
        if not (1 <= value <= 104):
            raise ValueError(f"invalid card value: {value}")

    def validate(self) -> None:
        self.validate_value(self.value)

    @property
    def bullheads(self) -> int:
        return bullheads(self.value)


@dataclass(slots=True)
class Deck:
    cards: list[Card] = field(default_factory=list)

    @classmethod
    def create_standard_deck(cls) -> "Deck":
        return cls(cards=[Card(value) for value in range(1, 105)])

    def validate(self) -> None:
        seen_values: set[int] = set()

        for card in self.cards:
            card.validate()

            if card.value in seen_values:
                raise ValueError(f"duplicate card value in deck: {card.value}")
            seen_values.add(card.value)

    def validate_standard_deck(self) -> None:
        self.validate()

        values = {card.value for card in self.cards}
        expected = set(range(1, 105))
        if values != expected:
            raise ValueError("deck is not a complete standard deck")

    def shuffle(self, rng: random.Random | None = None) -> None:
        if rng is None:
            random.shuffle(self.cards)
            return
        rng.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            raise ValueError("cannot draw from empty deck")
        return self.cards.pop()

    def draw_many(self, count: int) -> list[Card]:
        if count < 0:
            raise ValueError(f"count must be >= 0, got {count}")
        if count > len(self.cards):
            raise ValueError(
                f"cannot draw {count} cards from deck with {len(self.cards)} cards"
            )

        return [self.draw() for _ in range(count)]

    def contains(self, card: Card) -> bool:
        return card in self.cards

    def contains_value(self, value: int) -> bool:
        return any(card.value == value for card in self.cards)

    def __len__(self) -> int:
        return len(self.cards)
