from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.state import DeltaPublicState, PlayerState, PublicState
from row_taker.engine.lobby.config import MatchConfig
from row_taker.engine.lobby.state import LobbyState


@dataclass(frozen=True, slots=True)
class ConfigureLobby:
    match_config: MatchConfig


@dataclass(frozen=True, slots=True)
class StartGame:
    pass


@dataclass(frozen=True, slots=True)
class SubmitCard:
    player_id: PlayerID
    card_value: int


@dataclass(frozen=True, slots=True)
class SubmitRowChoice:
    player_id: PlayerID
    row_id: RowID


ClientToServerMessage = ConfigureLobby | StartGame | SubmitCard | SubmitRowChoice


@dataclass(frozen=True, slots=True)
class LobbyStateUpdated:
    lobby_state: LobbyState


@dataclass(frozen=True, slots=True)
class GameStarting:
    lobby_state: LobbyState


@dataclass(frozen=True, slots=True)
class StateUpdated:
    state: PublicState


@dataclass(frozen=True, slots=True)
class ChooseCardRequested:
    player_id: PlayerID
    state: PlayerState


@dataclass(frozen=True, slots=True)
class ChooseRowRequested:
    player_id: PlayerID
    state: PlayerState


@dataclass(frozen=True, slots=True)
class TrickResolved:
    deltas: tuple[DeltaPublicState, ...]
    new_round_started: bool
    game_finished: bool


@dataclass(frozen=True, slots=True)
class ServerError:
    message: str


ServerToClientMessage = (
    LobbyStateUpdated
    | GameStarting
    | StateUpdated
    | ChooseCardRequested
    | ChooseRowRequested
    | TrickResolved
    | ServerError
)

GameClientMessage = SubmitCard | SubmitRowChoice
GameServerMessage = StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved
