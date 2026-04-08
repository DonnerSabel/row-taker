import random

from row_taker.protocol.messages import (
    AssignSeatToClient,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    RequestStartGame,
    SetDisplayName,
    StateUpdated,
)
from row_taker.server.local_server import LocalServer


def test_local_server_starts_match_from_multiclient_lobby_messages() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)

    server.handle_client_message('client-0', JoinLobby(display_name='Alice'))
    server.handle_client_message('client-1', JoinLobby(display_name='Bob'))
    server.handle_client_message('client-0', AssignSeatToClient(seat_index=0, target_client_id='client-0'))
    server.handle_client_message('client-1', AssignSeatToClient(seat_index=1, target_client_id='client-1'))
    server.drain_outbox()

    server.handle_client_message('client-0', RequestStartGame())
    messages = [envelope.message for envelope in server.drain_outbox()]

    assert isinstance(messages[0], GameStarting)
    assert any(isinstance(message, StateUpdated) for message in messages)


def test_local_server_can_add_bot_on_selected_seat() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message('client-0', JoinLobby(display_name='Alice'))
    server.handle_client_message('client-0', AssignSeatToClient(seat_index=0, target_client_id='client-0'))
    server.handle_client_message('client-0', CreateLocalBotOnSeat(seat_index=1, display_name='Bot_Bob'))
    lobby = server.drain_outbox()[-1].message.lobby
    seat = next(seat for seat in lobby.seats if seat.seat_index == 1)
    assert seat.occupant_client_id is not None
    assert seat.occupant_display_name == 'Bot_Bob'


def test_registry_is_only_source_of_participant_metadata() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message('client-0', JoinLobby(display_name='Alice'))
    server.handle_client_message('client-0', SetDisplayName(display_name='Alicia'))
    participant = server.registry.get_participant('client-0')
    assert participant.display_name == 'Alicia'
    assert not hasattr(server.lobby_state, 'clients')
