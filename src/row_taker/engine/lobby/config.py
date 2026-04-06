from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final


MIN_PLAYERS: Final[int] = 2
MAX_PLAYERS: Final[int] = 6


class ClientKind(str, Enum):
    HUMAN = "human"
    RANDOM_BOT = "random_bot"


@dataclass(slots=True, frozen=True)
class SeatConfig:
    seat_index: int
    kind: ClientKind
    name: str

    @staticmethod
    def human(seat_index: int, name: str) -> "SeatConfig":
        return SeatConfig(seat_index=seat_index, kind=ClientKind.HUMAN, name=name)

    @staticmethod
    def random_bot(seat_index: int, name: str) -> "SeatConfig":
        return SeatConfig(seat_index=seat_index, kind=ClientKind.RANDOM_BOT, name=name)

    def validate(self) -> None:
        if self.seat_index < 0:
            raise ValueError(f"seat_index must be >= 0, got {self.seat_index}")
        if not self.name.strip():
            raise ValueError("seat name must not be empty")


@dataclass(slots=True, frozen=True)
class MatchConfig:
    seats: tuple[SeatConfig, ...] = field(default_factory=tuple)

    @staticmethod
    def from_seats(seats: list[SeatConfig] | tuple[SeatConfig, ...]) -> "MatchConfig":
        config = MatchConfig(seats=tuple(seats))
        config.validate()
        return config

    def validate(self) -> None:
        player_count = len(self.seats)
        if not (MIN_PLAYERS <= player_count <= MAX_PLAYERS):
            raise ValueError(
                f"player count must be between {MIN_PLAYERS} and {MAX_PLAYERS}, got {player_count}"
            )

        seen_indices: set[int] = set()
        seen_names: set[str] = set()

        for seat in self.seats:
            seat.validate()

            if seat.seat_index in seen_indices:
                raise ValueError(f"duplicate seat_index: {seat.seat_index}")
            seen_indices.add(seat.seat_index)

            normalized_name = seat.name.strip().casefold()
            if normalized_name in seen_names:
                raise ValueError(f"duplicate player name: {seat.name!r}")
            seen_names.add(normalized_name)

        expected_indices = set(range(player_count))
        if seen_indices != expected_indices:
            raise ValueError(
                f"seat indices must be contiguous starting at 0, got {sorted(seen_indices)}"
            )

    @property
    def player_count(self) -> int:
        return len(self.seats)
