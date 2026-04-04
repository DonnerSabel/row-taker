from dataclasses import dataclass, field

from .commands import ChooseRowCommand, PlayCardCommand
from .models import Card, Player, PlayerID, PublicPlayerInfo, Row, RowID
from .phases import PhaseInfo


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


@dataclass(slots=True)
class GameState:
    config: RulesConfig
    players: list[Player]
    rows: list[Row]
    deck: list[Card]

    round_no: int = 1
    trick_no: int = 1

    phase_info: PhaseInfo = field(default_factory=lambda: PhaseInfo(phase='round_setup'))

    selected_cards: dict[PlayerID, Card] = field(default_factory=dict)
    resolve_order: list[PlayerID] = field(default_factory=list)

    def validate_player_id(self, player_id: PlayerID) -> None:
        if all(player.player_id != player_id for player in self.players):
            raise ValueError(f"unknown player_id: {player_id!r}")

    def get_player_by_id(self, player_id: PlayerID) -> Player:
        self.validate_player_id(player_id)
        for player in self.players:
            if player.player_id == player_id:
                return player
        raise AssertionError('validate_player_id accepted an unknown player_id')

    def validate_row_id(self, row_id: RowID) -> None:
        if all(row.row_id != row_id for row in self.rows):
            raise ValueError(f"unknown row_id: {row_id!r}")

    def get_row_index(self, row_id: RowID) -> int:
        self.validate_row_id(row_id)
        for index, row in enumerate(self.rows):
            if row.row_id == row_id:
                return index
        raise AssertionError('validate_row_id accepted an unknown row_id')

    def validate_complete_play_selections(self, selections: dict[PlayerID, Card | PlayCardCommand]) -> None:
        expected_player_ids = {player.player_id for player in self.players}
        if set(selections.keys()) != expected_player_ids:
            raise ValueError('selections must contain one card for every player_id')

    def validate_player_has_card(self, player_id: PlayerID, card: Card) -> None:
        player = self.get_player_by_id(player_id)
        if all(hand_card.value != card.value for hand_card in player.hand):
            raise ValueError(f"player {player_id!r} does not have card {card.value}")

    def validate_play_command_player_id(self, expected_player_id: PlayerID, command: PlayCardCommand) -> None:
        if command.player_id != expected_player_id:
            raise ValueError(
                f"PlayCardCommand player_id mismatch: expected {expected_player_id!r}, got {command.player_id!r}"
            )

    def validate_choose_row_command_player_id(self, expected_player_id: PlayerID, command: ChooseRowCommand) -> None:
        if command.player_id != expected_player_id:
            raise ValueError(
                f"ChooseRowCommand player_id mismatch: expected {expected_player_id!r}, got {command.player_id!r}"
            )


@dataclass(frozen=True, slots=True)
class PlayerState:
    config: RulesConfig
    self_player_id: PlayerID

    players: list[PublicPlayerInfo]
    rows: list[Row]
    hand: list[Card]

    round_no: int
    trick_no: int
    phase_info: PhaseInfo

    def validate_phase(self, expected_phase: str) -> None:
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
        if all(row.row_id != row_id for row in self.rows):
            raise ValueError(f"unknown row_id: {row_id!r}")

    def get_row_index(self, row_id: RowID) -> int:
        self.validate_row_id(row_id)
        for index, row in enumerate(self.rows):
            if row.row_id == row_id:
                return index
        raise AssertionError('validate_row_id accepted an unknown row_id')

    def get_selectable_row_ids_for_choose_row(self) -> tuple[RowID, ...]:
        selectable_row_ids = tuple(self.phase_info.selectable_row_ids)
        if selectable_row_ids:
            return selectable_row_ids
        return tuple(row.row_id for row in self.rows)

    def validate_selectable_row_id(self, row_id: RowID) -> None:
        selectable_row_ids = self.get_selectable_row_ids_for_choose_row()
        if row_id not in selectable_row_ids:
            raise ValueError(f"row_id {row_id!r} is not selectable in the current state")
