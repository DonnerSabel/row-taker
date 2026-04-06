from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .cards import Card
from .models import Player, PlayerID, PublicPlayerInfo, Row, RowID
from .phases import Phase, PhaseInfo


def get_player_index(players: Sequence[Player | PublicPlayerInfo], player_id: PlayerID) -> int:
    for index, player in enumerate(players):
        if player.player_id == player_id:
            return index
    raise ValueError(f"unknown player_id: {player_id!r}")


def get_row_index(rows: Sequence[Row], row_id: RowID) -> int:
    for index, row in enumerate(rows):
        if row.row_id == row_id:
            return index
    raise ValueError(f"unknown row_id: {row_id!r}")


@dataclass(frozen=True, slots=True)
class RulesConfig:
    hand_size: int = 10
    row_count: int = 4
    row_capacity: int = 5
    end_score: int = 66

    @staticmethod
    def validate_player_count(player_count: int) -> None:
        if not (2 <= player_count <= 6):
            raise ValueError(f"player count must be 2..6, got {player_count}")


@dataclass(frozen=True, slots=True)
class DeltaPublicState:
    player_id: PlayerID
    affected_row_id: RowID
    new_row_cards: tuple[Card, ...]

    def played_card(self) -> Card:
        if not self.new_row_cards:
            raise ValueError('delta public state must contain at least one row card')
        return self.new_row_cards[-1]


@dataclass(slots=True)
class GameState:
    config: RulesConfig
    players: list[Player]
    rows: list[Row]
    deck: list[Card]

    round_no: int = 1
    trick_no: int = 1

    phase_info: PhaseInfo = field(default_factory=lambda: PhaseInfo(phase=Phase.ROUND_SETUP))

    selected_cards: dict[PlayerID, Card] = field(default_factory=dict)
    resolve_order: list[PlayerID] = field(default_factory=list)

    def validate_player_id(self, player_id: PlayerID) -> None:
        get_player_index(self.players, player_id)

    def get_player_by_id(self, player_id: PlayerID) -> Player:
        return self.players[get_player_index(self.players, player_id)]

    def validate_row_id(self, row_id: RowID) -> None:
        get_row_index(self.rows, row_id)

    def get_row_index(self, row_id: RowID) -> int:
        return get_row_index(self.rows, row_id)

    def validate_complete_play_selections(self) -> None:
        expected_player_ids = {player.player_id for player in self.players}
        if set(self.selected_cards.keys()) != expected_player_ids:
            raise ValueError('selections must contain one card for every player_id')

    def validate_player_has_card(self, player_id: PlayerID, card: Card) -> None:
        player = self.get_player_by_id(player_id)
        if all(hand_card.value != card.value for hand_card in player.hand):
            raise ValueError(f"player {player_id!r} does not have card {card.value}")

    def validate_no_selected_card_for_player(self, player_id: PlayerID) -> None:
        if player_id in self.selected_cards:
            raise ValueError(f"player {player_id!r} has already selected a card")


@dataclass(frozen=True, slots=True)
class PublicState:
    config: RulesConfig
    players: list[PublicPlayerInfo]
    rows: list[Row]
    round_no: int
    trick_no: int
    phase_info: PhaseInfo

    def validate_row_id(self, row_id: RowID) -> None:
        get_row_index(self.rows, row_id)

    def get_row_index(self, row_id: RowID) -> int:
        return get_row_index(self.rows, row_id)


@dataclass(frozen=True, slots=True)
class PlayerState:
    public_state: PublicState
    self_player_id: PlayerID
    hand: list[Card]

    def validate_phase(self, expected_phase: Phase) -> None:
        if self.phase_info.phase != expected_phase:
            raise ValueError(
                f"invalid phase: expected {expected_phase!r}, got {self.phase_info.phase!r}"
            )

    def validate_hand_not_empty(self) -> None:
        if not self.hand:
            raise ValueError('player hand is empty')

    def validate_has_card(self, card: Card) -> None:
        if all(hand_card.value != card.value for hand_card in self.hand):
            raise ValueError(f"player does not have card {card.value}")

    def validate_row_id(self, row_id: RowID) -> None:
        self.public_state.validate_row_id(row_id)

    def get_row_index(self, row_id: RowID) -> int:
        return self.public_state.get_row_index(row_id)

    def get_selectable_row_ids_for_choose_row(self) -> tuple[RowID, ...]:
        selectable_row_ids = tuple(self.phase_info.selectable_row_ids)
        if selectable_row_ids:
            return selectable_row_ids
        return tuple(row.row_id for row in self.rows)

    def validate_selectable_row_id(self, row_id: RowID) -> None:
        selectable_row_ids = self.get_selectable_row_ids_for_choose_row()
        if row_id not in selectable_row_ids:
            raise ValueError(f"row_id {row_id!r} is not selectable in the current state")

    @property
    def config(self) -> RulesConfig:
        return self.public_state.config

    @property
    def players(self) -> list[PublicPlayerInfo]:
        return self.public_state.players

    @property
    def rows(self) -> list[Row]:
        return self.public_state.rows

    @property
    def round_no(self) -> int:
        return self.public_state.round_no

    @property
    def trick_no(self) -> int:
        return self.public_state.trick_no

    @property
    def phase_info(self) -> PhaseInfo:
        return self.public_state.phase_info
