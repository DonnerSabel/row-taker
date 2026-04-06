import random

from row_taker.protocol.messages import (
    ChooseSeat,
    FillEmptySeatsWithBots,
    GameStarting,
    JoinLobby,
    LobbyStateUpdated,
    RequestStartGame,
    StateUpdated,
)
from row_taker.server.local_server import LocalServer


def test_local_server_starts_match_from_multiclient_lobby_messages() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)

    server.handle_client_message('client-0', JoinLobby(display_name='Alice'))
    server.handle_client_message('client-1', JoinLobby(display_name='Bob'))
    server.handle_client_message('client-0', ChooseSeat(seat_index=0))
    server.handle_client_message('client-1', ChooseSeat(seat_index=1))
    server.drain_outbox()

    server.handle_client_message('client-0', RequestStartGame())
    messages = [envelope.message for envelope in server.drain_outbox()]

    assert isinstance(messages[0], GameStarting)
    assert any(isinstance(message, StateUpdated) for message in messages)


def test_local_server_can_fill_bots() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message('client-0', JoinLobby(display_name='Alice'))
    server.handle_client_message('client-0', ChooseSeat(seat_index=0))
    server.handle_client_message('client-0', FillEmptySeatsWithBots())
    messages = server.drain_outbox()
    assert any(isinstance(envelope.message, LobbyStateUpdated) for envelope in messages)
