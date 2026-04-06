from __future__ import annotations

from dataclasses import dataclass, field
import random

from row_taker.engine.game import setup_game
from row_taker.engine.game.state import GameState, PublicState
from row_taker.engine.lobby.rules import can_start_game, validate_lobby_state
from row_taker.engine.lobby.state import LobbyState
from row_taker.hub.match_hub import MatchHub
from row_taker.protocol.messages import (
    ClientToServerMessage,
    ConfigureLobby,
    GameStarting,
    LobbyStateUpdated,
    ServerToClientMessage,
    StartGame,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(slots=True)
class LocalServer:
    rng: random.Random
    lobby_state: LobbyState = field(default_factory=LobbyState)
    active_match: MatchHub | None = None
    outbox: list[ServerToClientMessage] = field(default_factory=list)

    def handle_client_message(self, message: ClientToServerMessage) -> None:
        if isinstance(message, ConfigureLobby):
            self._handle_configure_lobby(message)
            return
        if isinstance(message, StartGame):
            self._handle_start_game()
            return
        if isinstance(message, (SubmitCard, SubmitRowChoice)):
            self._forward_game_message(message)
            return
        raise TypeError(f"unsupported client message type: {type(message)!r}")

    def drain_outbox(self) -> list[ServerToClientMessage]:
        drained = list(self.outbox)
        self.outbox.clear()
        return drained

    def build_public_state(self) -> PublicState:
        if self.active_match is None:
            raise ValueError("no active match")
        return self.active_match.build_public_state()

    @property
    def state(self) -> GameState:
        if self.active_match is None:
            raise ValueError("no active match")
        return self.active_match.state

    def _handle_configure_lobby(self, message: ConfigureLobby) -> None:
        if self.active_match is not None:
            raise ValueError("cannot reconfigure lobby after the game has started")
        self.lobby_state = LobbyState(match_config=message.match_config, game_started=False)
        validate_lobby_state(self.lobby_state)
        self.outbox.append(LobbyStateUpdated(lobby_state=self.lobby_state))

    def _handle_start_game(self) -> None:
        if self.active_match is not None:
            raise ValueError("game already started")
        if not can_start_game(self.lobby_state):
            raise ValueError("cannot start game without valid lobby configuration")

        self.lobby_state = LobbyState(match_config=self.lobby_state.match_config, game_started=True)
        self.outbox.append(GameStarting(lobby_state=self.lobby_state))

        match_config = self.lobby_state.match_config
        if match_config is None:
            raise ValueError("missing match configuration")

        player_names = [seat.name for seat in match_config.seats]
        state = setup_game(player_names, rng=self.rng)
        self.active_match = MatchHub(state=state)
        self.active_match.start_match()
        self.outbox.extend(self.active_match.drain_outbox())

    def _forward_game_message(self, message: SubmitCard | SubmitRowChoice) -> None:
        if self.active_match is None:
            raise ValueError("game message received before start_game")
        self.active_match.handle_client_message(message)
        self.outbox.extend(self.active_match.drain_outbox())
