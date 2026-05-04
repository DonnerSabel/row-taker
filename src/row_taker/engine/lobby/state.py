from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LobbySeat:
    seat_index: int
    occupant_client_id: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.occupant_client_id is None


@dataclass(slots=True, frozen=True)
class LobbyState:
    seat_count: int = 4
    seats: tuple[LobbySeat, ...] = ()
    game_started: bool = False

    def __post_init__(self) -> None:
        if self.seat_count < 2:
            raise ValueError("seat_count must be at least 2")
        if not self.seats:
            object.__setattr__(
                self, "seats", tuple(LobbySeat(seat_index=i) for i in range(self.seat_count))
            )
        elif len(self.seats) != self.seat_count:
            raise ValueError("len(seats) must equal seat_count")

    @property
    def is_configured(self) -> bool:
        return True

    def seat_for_client(self, client_id: str) -> LobbySeat | None:
        for seat in self.seats:
            if seat.occupant_client_id == client_id:
                return seat
        return None

    def occupant_client_id_for_seat(self, seat_index: int) -> str | None:
        return self.seats[seat_index].occupant_client_id


def ordered_seated_client_ids(state: LobbyState) -> tuple[str, ...]:
    return tuple(
        seat.occupant_client_id
        for seat in sorted(state.seats, key=lambda seat: seat.seat_index)
        if seat.occupant_client_id is not None
    )
