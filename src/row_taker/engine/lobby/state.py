from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.lobby.config import ClientKind, MatchConfig, SeatConfig


@dataclass(slots=True, frozen=True)
class ConnectedClient:
    client_id: str
    display_name: str


@dataclass(slots=True, frozen=True)
class LobbySeat:
    seat_index: int
    kind: ClientKind | None = None
    name: str | None = None
    client_id: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.kind is None

    @property
    def is_human(self) -> bool:
        return self.kind == ClientKind.HUMAN

    @property
    def is_bot(self) -> bool:
        return self.kind == ClientKind.RANDOM_BOT


@dataclass(slots=True, frozen=True)
class LobbyState:
    seat_count: int = 4
    clients: tuple[ConnectedClient, ...] = ()
    seats: tuple[LobbySeat, ...] = ()
    game_started: bool = False

    def __post_init__(self) -> None:
        if self.seat_count < 2:
            raise ValueError('seat_count must be at least 2')
        if not self.seats:
            object.__setattr__(self, 'seats', tuple(LobbySeat(seat_index=i) for i in range(self.seat_count)))
        elif len(self.seats) != self.seat_count:
            raise ValueError('len(seats) must equal seat_count')

    @property
    def is_configured(self) -> bool:
        return True

    def get_client(self, client_id: str) -> ConnectedClient:
        for client in self.clients:
            if client.client_id == client_id:
                return client
        raise KeyError(client_id)

    def seat_for_client(self, client_id: str) -> LobbySeat | None:
        for seat in self.seats:
            if seat.client_id == client_id:
                return seat
        return None

    def to_match_config(self) -> MatchConfig:
        config_seats: list[SeatConfig] = []
        for seat in self.seats:
            if seat.kind is None or seat.name is None:
                raise ValueError('cannot build match config from incomplete lobby')
            config_seats.append(SeatConfig(seat_index=seat.seat_index, kind=seat.kind, name=seat.name))
        config_seats.sort(key=lambda seat: seat.seat_index)
        return MatchConfig.from_seats(config_seats)
