import random

from row_taker.engine.lobby.config import MatchConfig, SeatConfig
from row_taker.engine.lobby.state import LobbyState
from row_taker.protocol.messages import ConfigureLobby, GameStarting, LobbyStateUpdated, StartGame, StateUpdated
from row_taker.server.local_server import LocalServer


def test_local_server_starts_match_from_lobby_messages() -> None:
    server = LocalServer(rng=random.Random(1234))
    config = MatchConfig.from_seats([
        SeatConfig.human(0, 'A'),
        SeatConfig.random_bot(1, 'Bot_1'),
    ])

    server.handle_client_message(ConfigureLobby(match_config=config))
    messages = server.drain_outbox()
    assert messages == [LobbyStateUpdated(lobby_state=LobbyState(match_config=config, game_started=False))]

    server.handle_client_message(StartGame())
    messages = server.drain_outbox()

    assert isinstance(messages[0], GameStarting)
    assert messages[0].lobby_state == LobbyState(match_config=config, game_started=True)
    assert any(isinstance(message, StateUpdated) for message in messages)
