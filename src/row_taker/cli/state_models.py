from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import LobbyView, TrickResolved, TrickRevealed


@dataclass(frozen=True, slots=True)
class UiMessage:
    level: Literal["info", "error"]
    text: str


@dataclass(frozen=True, slots=True)
class LobbyScreen:
    kind: Literal["main", "rename", "seat_edit", "bot_name"]
    seat_index: int | None = None


@dataclass(frozen=True, slots=True)
class GameScreen:
    kind: Literal["waiting", "choose_card", "choose_row", "ended"]
    player_state: PlayerState | None = None


Screen = LobbyScreen | GameScreen


@dataclass(frozen=True, slots=True)
class TrickResolvedModal:
    public_state_before: PublicState | None
    resolved: TrickResolved


ModalDialog = TrickResolvedModal


@dataclass(frozen=True, slots=True)
class CliState:
    own_client_id: str | None = None
    own_player_id: str | None = None
    lobby_view: LobbyView | None = None
    public_state: PublicState | None = None
    screen: Screen = field(default_factory=lambda: LobbyScreen(kind="main"))
    modal: ModalDialog | None = None
    flash_message: UiMessage | None = None
    revealed_trick: TrickRevealed | None = None
    session_error: str | None = None
    exit_on_ack: bool = False
    suppress_final_result: bool = False
    should_exit: bool = False


LobbyStateMain = LobbyScreen
LobbyStateRename = LobbyScreen
LobbyStateSeatEdit = LobbyScreen
GameStateWaiting = GameScreen
GameStateChooseCard = GameScreen
GameStateChooseRow = GameScreen
GameStateEnded = GameScreen
GameStateTrickResolved = TrickResolvedModal


def initial_cli_state(own_client_id: str | None = None) -> CliState:
    return CliState(own_client_id=own_client_id)
