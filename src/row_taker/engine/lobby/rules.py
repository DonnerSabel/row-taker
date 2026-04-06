from __future__ import annotations

from row_taker.engine.lobby.config import ClientKind, MAX_PLAYERS, MIN_PLAYERS
from row_taker.engine.lobby.state import ConnectedClient, LobbySeat, LobbyState


def validate_lobby_state(lobby_state: LobbyState) -> None:
    if not (MIN_PLAYERS <= lobby_state.seat_count <= MAX_PLAYERS):
        raise ValueError(
            f'seat_count must be between {MIN_PLAYERS} and {MAX_PLAYERS}, got {lobby_state.seat_count}'
        )
    if len({client.client_id for client in lobby_state.clients}) != len(lobby_state.clients):
        raise ValueError('duplicate client ids in lobby')
    if len({client.display_name.strip().casefold() for client in lobby_state.clients}) != len(lobby_state.clients):
        raise ValueError('duplicate client display names in lobby')

    seen_seats: set[int] = set()
    seen_human_client_ids: set[str] = set()
    seen_names: set[str] = set()
    for seat in lobby_state.seats:
        if seat.seat_index in seen_seats:
            raise ValueError(f'duplicate seat index {seat.seat_index}')
        seen_seats.add(seat.seat_index)
        if seat.kind is None:
            if seat.name is not None or seat.client_id is not None:
                raise ValueError('empty seats must not have name or client_id')
            continue
        if not seat.name or not seat.name.strip():
            raise ValueError('occupied seats must have a non-empty name')
        norm_name = seat.name.strip().casefold()
        if norm_name in seen_names:
            raise ValueError(f'duplicate seat/player name {seat.name!r}')
        seen_names.add(norm_name)
        if seat.kind == ClientKind.HUMAN:
            if seat.client_id is None:
                raise ValueError('human seat missing client_id')
            if seat.client_id in seen_human_client_ids:
                raise ValueError('a client may occupy at most one seat')
            seen_human_client_ids.add(seat.client_id)
        else:
            if seat.client_id is not None:
                raise ValueError('bot seat must not carry a client_id')
    if seen_seats != set(range(lobby_state.seat_count)):
        raise ValueError('seat indices must be contiguous from 0')


def join_lobby(lobby_state: LobbyState, client_id: str, display_name: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    if any(client.client_id == client_id for client in lobby_state.clients):
        raise ValueError(f'client {client_id!r} already joined')
    clients = list(lobby_state.clients)
    clients.append(ConnectedClient(client_id=client_id, display_name=_validate_display_name(display_name)))
    new_state = LobbyState(
        seat_count=lobby_state.seat_count,
        clients=tuple(clients),
        seats=lobby_state.seats,
        game_started=lobby_state.game_started,
    )
    validate_lobby_state(new_state)
    return new_state


def remove_client(lobby_state: LobbyState, client_id: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    clients = tuple(client for client in lobby_state.clients if client.client_id != client_id)
    seats = []
    for seat in lobby_state.seats:
        if seat.client_id == client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index))
        else:
            seats.append(seat)
    new_state = LobbyState(
        seat_count=lobby_state.seat_count,
        clients=clients,
        seats=tuple(seats),
        game_started=lobby_state.game_started,
    )
    validate_lobby_state(new_state)
    return new_state


def set_display_name(lobby_state: LobbyState, client_id: str, display_name: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    validated_name = _validate_display_name(display_name)
    found = False
    clients = []
    for client in lobby_state.clients:
        if client.client_id == client_id:
            clients.append(ConnectedClient(client_id=client.client_id, display_name=validated_name))
            found = True
        else:
            clients.append(client)
    if not found:
        raise ValueError(f'unknown client_id: {client_id!r}')
    seats = []
    for seat in lobby_state.seats:
        if seat.client_id == client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index, kind=seat.kind, name=validated_name, client_id=client_id))
        else:
            seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, tuple(clients), tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def choose_seat(lobby_state: LobbyState, client_id: str, seat_index: int) -> LobbyState:
    validate_lobby_state(lobby_state)
    client = lobby_state.get_client(client_id)
    if not (0 <= seat_index < lobby_state.seat_count):
        raise ValueError(f'seat index out of range: {seat_index}')
    seats = []
    for seat in lobby_state.seats:
        if seat.client_id == client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index))
            continue
        if seat.seat_index == seat_index:
            if not seat.is_empty:
                raise ValueError(f'seat {seat_index + 1} is already occupied')
            seats.append(LobbySeat(seat_index=seat.seat_index, kind=ClientKind.HUMAN, name=client.display_name, client_id=client_id))
            continue
        seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, lobby_state.clients, tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def leave_seat(lobby_state: LobbyState, client_id: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    seats = []
    for seat in lobby_state.seats:
        if seat.client_id == client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index))
        else:
            seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, lobby_state.clients, tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def fill_empty_seats_with_bots(lobby_state: LobbyState) -> LobbyState:
    validate_lobby_state(lobby_state)
    seats = []
    for seat in lobby_state.seats:
        if seat.is_empty:
            seat_no = seat.seat_index + 1
            seats.append(LobbySeat(seat_index=seat.seat_index, kind=ClientKind.RANDOM_BOT, name=f'Bot_{seat_no}'))
        else:
            seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, lobby_state.clients, tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def clear_bot_seats(lobby_state: LobbyState) -> LobbyState:
    validate_lobby_state(lobby_state)
    seats = []
    for seat in lobby_state.seats:
        if seat.is_bot:
            seats.append(LobbySeat(seat_index=seat.seat_index))
        else:
            seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, lobby_state.clients, tuple(seats), lobby_state.game_started)
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
        clients=lobby_state.clients,
        seats=lobby_state.seats,
        game_started=True,
    )


def _validate_display_name(display_name: str) -> str:
    value = display_name.strip()
    if not value:
        raise ValueError('display name must not be empty')
    return value
