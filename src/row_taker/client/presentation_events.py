from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.models import PlayerID, RowID
from row_taker.protocol.messages import PlayedCardView


@dataclass(frozen=True, slots=True)
class PresentationEvent:
    pass


@dataclass(frozen=True, slots=True)
class PresentationCardsRevealed(PresentationEvent):
    plays: tuple[PlayedCardView, ...]


@dataclass(frozen=True, slots=True)
class PresentationCardPlaced(PresentationEvent):
    player_id: PlayerID
    player_name: str
    card_value: int
    row_id: RowID
    row_cards_after: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PresentationRowChoiceRequired(PresentationEvent):
    player_id: PlayerID
    player_name: str
    card_value: int


@dataclass(frozen=True, slots=True)
class PresentationRowChosen(PresentationEvent):
    player_id: PlayerID
    player_name: str
    row_id: RowID
    card_value: int


@dataclass(frozen=True, slots=True)
class PresentationRowTaken(PresentationEvent):
    player_id: PlayerID
    player_name: str
    row_id: RowID
    taken_cards: tuple[int, ...]
    bullheads: int
    replacement_card_value: int
    row_cards_after: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PresentationOverflowResolved(PresentationEvent):
    player_id: PlayerID
    player_name: str
    row_id: RowID
    card_value: int
    taken_cards: tuple[int, ...]
    bullheads: int
    row_cards_after: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PresentationTrickFinished(PresentationEvent):
    pass


@dataclass(frozen=True, slots=True)
class PresentationRoundFinished(PresentationEvent):
    pass


@dataclass(frozen=True, slots=True)
class PresentationGameFinished(PresentationEvent):
    pass
