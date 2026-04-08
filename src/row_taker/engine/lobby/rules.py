from __future__ import annotations

from row_taker.engine.lobby.config import ClientKind, MAX_PLAYERS, MIN_PLAYERS
from row_taker.engine.lobby.state import ConnectedClient, LobbySeat, LobbyState


BOT_PREFIX = 'bot-'


def validate_lobby_state(lobby_state: LobbyState) -> None:
    if not (MIN_PLAYERS <= lobby_state.seat_count <= MAX_PLAYERS):
        raise ValueError(
            f'seat_count must be between {MIN_PLAYERS} and {MAX_PLAYERS}, got {lobby_state.seat_count}'
        )
    if len({client.client_id for client in lobby_state.clients}) != len(lobby_state.clients):
        raise ValueError('duplicate client ids in lobby')
    normalized_names = [client.display_name.strip().casefold() for client in lobby_state.clients]
    if len(set(normalized_names)) != len(normalized_names):
        raise ValueError('duplicate client display names in lobby')

    seen_seats: set[int] = set()
    seen_occupants: set[str] = set()
    known_client_ids = {client.client_id for client in lobby_state.clients}
    for seat in lobby_state.seats:
        if seat.seat_index in seen_seats:
            raise ValueError(f'duplicate seat index {seat.seat_index}')
        seen_seats.add(seat.seat_index)
        if seat.occupant_client_id is None:
            continue
        if seat.occupant_client_id not in known_client_ids:
            raise ValueError(f'unknown occupant client_id: {seat.occupant_client_id!r}')
        if seat.occupant_client_id in seen_occupants:
            raise ValueError('a client may occupy at most one seat')
        seen_occupants.add(seat.occupant_client_id)
    if seen_seats != set(range(lobby_state.seat_count)):
        raise ValueError('seat indices must be contiguous from 0')


def join_lobby(lobby_state: LobbyState, client_id: str, display_name: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    if any(client.client_id == client_id for client in lobby_state.clients):
        raise ValueError(f'client {client_id!r} already joined')
    clients = list(lobby_state.clients)
    clients.append(ConnectedClient(client_id=client_id, display_name=_validate_display_name(display_name), kind=ClientKind.HUMAN))
    new_state = LobbyState(
        seat_count=lobby_state.seat_count,
        clients=tuple(clients),
        seats=lobby_state.seats,
        game_started=lobby_state.game_started,
    )
    validate_lobby_state(new_state)
    return new_state


def add_local_bot(lobby_state: LobbyState, client_id: str, display_name: str) -> LobbyState:
    validate_lobby_state(lobby_state)
    if any(client.client_id == client_id for client in lobby_state.clients):
        raise ValueError(f'client {client_id!r} already exists')
    clients = list(lobby_state.clients)
    clients.append(ConnectedClient(client_id=client_id, display_name=_validate_display_name(display_name), kind=ClientKind.RANDOM_BOT))
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
        if seat.occupant_client_id == client_id:
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
            clients.append(ConnectedClient(client_id=client.client_id, display_name=validated_name, kind=client.kind))
            found = True
        else:
            clients.append(client)
    if not found:
        raise ValueError(f'unknown client_id: {client_id!r}')
    new_state = LobbyState(lobby_state.seat_count, tuple(clients), lobby_state.seats, lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def assign_client_to_seat(lobby_state: LobbyState, target_client_id: str, seat_index: int) -> LobbyState:
    validate_lobby_state(lobby_state)
    if not (0 <= seat_index < lobby_state.seat_count):
        raise ValueError(f'seat index out of range: {seat_index}')
    lobby_state.get_client(target_client_id)
    seats = []
    for seat in lobby_state.seats:
        if seat.occupant_client_id == target_client_id:
            seats.append(LobbySeat(seat_index=seat.seat_index))
            continue
        if seat.seat_index == seat_index:
            seats.append(LobbySeat(seat_index=seat.seat_index, occupant_client_id=target_client_id))
            continue
        seats.append(seat)
    new_state = LobbyState(lobby_state.seat_count, lobby_state.clients, tuple(seats), lobby_state.game_started)
    validate_lobby_state(new_state)
    return new_state


def clear_seat(lobby_state: LobbyState, seat_index: int) -> LobbyState:
    validate_lobby_state(lobby_state)
    if not (0 <= seat_index < lobby_state.seat_count):
        raise ValueError(f'seat index out of range: {seat_index}')
    seats = []
    for seat in lobby_state.seats:
        if seat.seat_index == seat_index:
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
