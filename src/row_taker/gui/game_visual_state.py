from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from row_taker.engine.game.models import PlayerID, RowID

RowEmphasis = Literal["none", "selectable", "placed", "choice", "taken", "overflow"]
PlayerEmphasis = Literal["none", "active"]
CardEmphasis = Literal["none", "selected"]
MessageLevel = Literal["normal", "info", "error"]


@dataclass(frozen=True, slots=True)
class VisualCard:
    card_value: int
    bullheads: int


@dataclass(frozen=True, slots=True)
class VisualRow:
    row_id: RowID
    cards: tuple[VisualCard, ...]
    emphasis: RowEmphasis = "none"
    taken_cards: tuple[VisualCard, ...] = ()

    @property
    def card_values(self) -> tuple[int, ...]:
        return tuple(card.card_value for card in self.cards)


@dataclass(frozen=True, slots=True)
class VisualPlayer:
    player_id: PlayerID
    name: str
    score: int
    hand_count: int
    is_self: bool
    staged_card_value: int | None = None
    emphasis: PlayerEmphasis = "none"


@dataclass(frozen=True, slots=True)
class VisualHandCard:
    card_value: int
    bullheads: int
    visible: bool = True
    emphasis: CardEmphasis = "none"


@dataclass(frozen=True, slots=True)
class VisualInteraction:
    selectable_card_values: frozenset[int] = frozenset()
    selectable_row_ids: frozenset[RowID] = frozenset()
    can_advance_presentation: bool = False


@dataclass(frozen=True, slots=True)
class VisualStatus:
    primary_line: str
    secondary_line: str
    message_level: MessageLevel = "normal"
    hand_prompt: str | None = None


@dataclass(frozen=True, slots=True)
class GameVisualState:
    """Complete semantic input for one stable game-screen frame.

    The model intentionally contains no pygame objects, pixel coordinates,
    fonts, colors, protocol messages, or client actions. Layout and hit testing
    are derived from this state by the production GUI.
    """

    rows: tuple[VisualRow, ...]
    players: tuple[VisualPlayer, ...]
    hand: tuple[VisualHandCard, ...]
    interaction: VisualInteraction
    status: VisualStatus

    @property
    def visible_hand(self) -> tuple[VisualHandCard, ...]:
        return tuple(card for card in self.hand if card.visible)

    @property
    def opponents(self) -> tuple[VisualPlayer, ...]:
        return tuple(player for player in self.players if not player.is_self)

    @property
    def own_player(self) -> VisualPlayer | None:
        return next((player for player in self.players if player.is_self), None)

    @property
    def own_player_id(self) -> PlayerID | None:
        player = self.own_player
        return None if player is None else player.player_id

    def row_by_id(self, row_id: RowID) -> VisualRow | None:
        return next((row for row in self.rows if row.row_id == row_id), None)
