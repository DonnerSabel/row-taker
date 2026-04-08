import random

from row_taker.protocol.messages import (
    AssignSeatToClient,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    RequestStartGame,
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
    lobby_state = server.drain_outbox()[-1].message.lobby_state
    assert lobby_state.occupant_for_seat(1) is not None
    assert lobby_state.occupant_for_seat(1).display_name == 'Bot_Bob'
