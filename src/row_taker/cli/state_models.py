from __future__ import annotations

from dataclasses import dataclass, field

from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import LobbyView, TrickResolved


@dataclass(frozen=True, slots=True)
class LobbyStateMain:
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class LobbyStateRename:
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class LobbyStateSeatEdit:
    seat_index: int
    error_message: str | None = None


LobbyMode = LobbyStateMain | LobbyStateRename | LobbyStateSeatEdit


@dataclass(frozen=True, slots=True)
class GameStateWaiting:
    info_message: str | None = None


@dataclass(frozen=True, slots=True)
class GameStateChooseCard:
    player_state: PlayerState
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class GameStateChooseRow:
    player_state: PlayerState
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class GameStateTrickResolved:
    public_state_before: PublicState | None
    resolved: TrickResolved
    info_message: str | None = None


@dataclass(frozen=True, slots=True)
class GameStateEnded:
    info_message: str | None = None


GameImmediateState = GameStateWaiting | GameStateChooseCard | GameStateChooseRow | GameStateEnded
GameMode = GameImmediateState | GameStateTrickResolved
CliMode = LobbyMode | GameMode


@dataclass(frozen=True, slots=True)
class CliState:
    own_client_id: str | None = None
    own_player_id: str | None = None
    lobby_view: LobbyView | None = None
    public_state: PublicState | None = None
    mode: CliMode = field(default_factory=LobbyStateMain)
    pending_next_state: GameImmediateState | None = None
    session_error: str | None = None
    should_exit: bool = False


def initial_cli_state(own_client_id: str | None = None) -> CliState:
    return CliState(own_client_id=own_client_id)

