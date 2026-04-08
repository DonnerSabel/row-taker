from __future__ import annotations

from row_taker.engine.lobby.config import MAX_PLAYERS, MIN_PLAYERS
from row_taker.engine.lobby.state import LobbySeat, LobbyState

BOT_PREFIX = "bot-"


def validate_lobby_state(lobby_state: LobbyState) -> None:
    if not (MIN_PLAYERS <= lobby_state.seat_count <= MAX_PLAYERS):
        raise ValueError(
            f"seat_count must be between {MIN_PLAYERS} and {MAX_PLAYERS}, got {lobby_state.seat_count}"
        )

    seen_seats: set[int] = set()
    seen_occupants: set[str] = set()
    for seat in lobby_state.seats:
        if seat.seat_index in seen_seats:
            raise ValueError(f"duplicate seat index {seat.seat_index}")
        seen_seats.add(seat.seat_index)
        if seat.occupant_client_id is None:
            continue
        if seat.occupant_client_id in seen_occupants:
            raise ValueError("a client may occupy at most one seat")
        seen_occupants.add(seat.occupant_client_id)
    if seen_seats != set(range(lobby_state.seat_count)):
        raise ValueError("seat indices must be contiguous from 0")


def remove_client(lobby_state: LobbyState, client_id: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    seats = []
    for seat in lobby_state.seats:
        if seat.occupant_client_id == client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index))
        else:
            seats.append(seat)
    new_state = LobbyState(
        seat_count=lobby_state.seat_count,
        seats=tuple(seats),
        game_started=lobby_state.game_started,
    )
    validate_lobby_state(new_state)
    return new_state


def assign_client_to_seat(
    lobby_state: LobbyState, target_client_id: str, seat_index: int
) -> LobbyState:
    validate_lobby_state(lobby_state)
    if not target_client_id.strip():
        raise ValueError("target_client_id must not be empty")
    if not (0 <= seat_index < lobby_state.seat_count):
        raise ValueError(f"seat index out of range: {seat_index}")
    seats = []
    for seat in lobby_state.seats:
        if seat.occupant_client_id == target_client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index))
            continue
        if seat.seat_index == seat_index:
            seats.append(LobbySeat(seat_index=seat.seat_index, occupant_client_id=target_client_id))
            continue
        seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def clear_seat(lobby_state: LobbyState, seat_index: int) -> LobbyState:
    validate_lobby_state(lobby_state)
    if not (0 <= seat_index < lobby_state.seat_count):
        raise ValueError(f"seat index out of range: {seat_index}")
    seats = []
    for seat in lobby_state.seats:
        if seat.seat_index == seat_index:
            seats.append(LobbySeat(seat_index=seat.seat_index))
        else:
            seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def can_start_game(lobby_state: LobbyState) -> bool:
    validate_lobby_state(lobby_state)
    if lobby_state.game_started:
        return False
    occupied = [seat for seat in lobby_state.seats if not seat.is_empty]
    if len(occupied) < MIN_PLAYERS:
        return False
    return len(occupied) == lobby_state.seat_count


def mark_game_started(lobby_state: LobbyState) -> LobbyState:
    validate_lobby_state(lobby_state)
    return LobbyState(
        seat_count=lobby_state.seat_count,
        seats=lobby_state.seats,
        game_started=True,
    )
