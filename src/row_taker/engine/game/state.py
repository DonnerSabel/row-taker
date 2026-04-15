from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .cards import Card
from .models import EngineRow, Player, PlayerID, PublicPlayerInfo, Row, RowID
from .phases import Phase, PhaseInfo, StepAction


def get_player_index(players: Sequence[Player | PublicPlayerInfo], player_id: PlayerID) -> int:
    for index, player in enumerate(players):
        if player.player_id == player_id:
            return index
    raise ValueError(f"unknown player_id: {player_id!r}")


def get_row_index(rows: Sequence[EngineRow | Row], row_id: RowID) -> int:
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
class RevealedPlay:
    player_id: PlayerID
    card: Card


@dataclass(frozen=True, slots=True)
class RowChoiceRequired:
    player_id: PlayerID
    card: Card
    selectable_row_ids: tuple[RowID, ...]


@dataclass(frozen=True, slots=True)
class TrickResolutionStep:
    action: StepAction
    player_id: PlayerID
    affected_row_id: RowID
    played_card: Card
    taken_cards: tuple[Card, ...]
    points_gained: int
    new_row_cards: tuple[Card, ...]


@dataclass(slots=True)
class TrickResolutionCursor:
    remaining_player_ids: list[PlayerID] = field(default_factory=list)
    steps: list[TrickResolutionStep] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class TrickResolutionSummary:
    steps: tuple[TrickResolutionStep, ...]
    new_round_started: bool
    game_finished: bool


@dataclass(slots=True)
class GameState:
    config: RulesConfig
    players: list[Player]
    rows: list[EngineRow]
    deck: list[Card]

    round_no: int = 1
    trick_no: int = 1

    phase_info: PhaseInfo = field(default_factory=lambda: PhaseInfo(phase=Phase.ROUND_SETUP))

    selected_cards: dict[PlayerID, Card] = field(default_factory=dict)
    current_trick_revealed_plays: tuple[RevealedPlay, ...] = ()
    resolution_cursor: TrickResolutionCursor | None = None

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
            raise ValueError("selections must contain one card for every player_id")

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
    players: tuple[PublicPlayerInfo, ...]
    rows: tuple[Row, ...]
    round_no: int
    trick_no: int
    phase_info: PhaseInfo

    def __post_init__(self) -> None:
        object.__setattr__(self, "players", tuple(self.players))
        object.__setattr__(self, "rows", tuple(self.rows))

    def validate_row_id(self, row_id: RowID) -> None:
        get_row_index(self.rows, row_id)

    def get_row_index(self, row_id: RowID) -> int:
        return get_row_index(self.rows, row_id)


@dataclass(frozen=True, slots=True)
class PlayerState:
    public_state: PublicState
    self_player_id: PlayerID
    hand: tuple[Card, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "hand", tuple(self.hand))

    def validate_phase(self, expected_phase: Phase) -> None:
        if self.phase_info.phase != expected_phase:
            raise ValueError(
                f"invalid phase: expected {expected_phase!r}, got {self.phase_info.phase!r}"
            )

    def validate_hand_not_empty(self) -> None:
        if not self.hand:
            raise ValueError("player hand is empty")

    def validate_has_card(self, card: Card) -> None:
        if all(hand_card.value != card.value for hand_card in self.hand):
            raise ValueError(f"player does not have card {card.value}")

    def validate_card_value(self, card_value: int) -> None:
        self.validate_has_card(Card(card_value))

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

    def self_player(self) -> PublicPlayerInfo:
        return self.players[get_player_index(self.players, self.self_player_id)]

    def self_player_name(self) -> str:
        return self.self_player().name

    def pending_card_value(self) -> int | None:
        if self.phase_info.pending_card is None:
            return None
        return self.phase_info.pending_card.value

    def playable_card_values(self) -> tuple[int, ...]:
        return tuple(card.value for card in self.hand)

    @property
    def config(self) -> RulesConfig:
        return self.public_state.config

    @property
    def players(self) -> tuple[PublicPlayerInfo, ...]:
        return self.public_state.players

    @property
    def rows(self) -> tuple[Row, ...]:
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
