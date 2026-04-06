import random

from row_taker.protocol.messages import ConfigureLobby, GameStarting, LobbyStateUpdated, StartGame, StateUpdated
from row_taker.server.local_server import LocalServer
from row_taker.hub.match_config import MatchConfig, SeatConfig


def test_local_server_starts_match_from_lobby_messages() -> None:
    server = LocalServer(rng=random.Random(1234))
    config = MatchConfig.from_seats([
        SeatConfig.human(0, 'A'),
        SeatConfig.random_bot(1, 'Bot_1'),
    ])

    server.handle_client_message(ConfigureLobby(match_config=config))
    messages = server.drain_outbox()
    assert messages == [LobbyStateUpdated(match_config=config)]

    server.handle_client_message(StartGame())
    messages = server.drain_outbox()

    assert isinstance(messages[0], GameStarting)
    assert messages[0].match_config == config
    assert any(isinstance(message, StateUpdated) for message in messages)
