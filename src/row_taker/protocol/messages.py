from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.models import PlayerID, RowID
from row_taker.engine.state import DeltaPublicState, PlayerState, PublicState
from row_taker.hub.match_config import MatchConfig


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
    match_config: MatchConfig


@dataclass(frozen=True, slots=True)
class GameStarting:
    match_config: MatchConfig


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


ServerToClientMessage = (
    LobbyStateUpdated
    | GameStarting
    | StateUpdated
    | ChooseCardRequested
    | ChooseRowRequested
    | TrickResolved
)

GameClientMessage = SubmitCard | SubmitRowChoice
GameServerMessage = StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved
