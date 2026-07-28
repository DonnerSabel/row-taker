from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeGuard

from row_taker.engine.game import GameState, PlayerID, PlayerState, PublicState, RowID
from row_taker.participants import ParticipantKind


@dataclass(frozen=True, slots=True)
class LobbyParticipantView:
    client_id: str
    display_name: str
    participant_kind: ParticipantKind
    seat_index: int | None
    endpoint: str | None = None


@dataclass(frozen=True, slots=True)
class LobbySeatView:
    seat_index: int
    occupant_client_id: str | None
    occupant_display_name: str | None
    occupant_kind: ParticipantKind | None
    occupant_endpoint: str | None = None


@dataclass(frozen=True, slots=True)
class LobbyView:
    seat_count: int
    participants: tuple[LobbyParticipantView, ...]
    seats: tuple[LobbySeatView, ...]
    game_started: bool
    server_endpoint: str | None = None


@dataclass(frozen=True, slots=True)
class JoinLobby:
    display_name: str
    requested_client_id: str | None = None


@dataclass(frozen=True, slots=True)
class SetDisplayName:
    display_name: str


@dataclass(frozen=True, slots=True)
class AssignSeatToClient:
    seat_index: int
    target_client_id: str


@dataclass(frozen=True, slots=True)
class CreateLocalBotOnSeat:
    seat_index: int
    display_name: str


@dataclass(frozen=True, slots=True)
class ClearSeat:
    seat_index: int


@dataclass(frozen=True, slots=True)
class RequestStartGame:
    pass


@dataclass(frozen=True, slots=True)
class LeaveSession:
    pass


@dataclass(frozen=True, slots=True)
class SubmitCard:
    card_value: int


@dataclass(frozen=True, slots=True)
class SubmitRowChoice:
    row_id: RowID


ClientToServerMessage = (
    JoinLobby
    | SetDisplayName
    | AssignSeatToClient
    | CreateLocalBotOnSeat
    | ClearSeat
    | RequestStartGame
    | LeaveSession
    | SubmitCard
    | SubmitRowChoice
)


@dataclass(frozen=True, slots=True)
class IdentityAssigned:
    client_id: str


@dataclass(frozen=True, slots=True)
class LobbyStateUpdated:
    lobby: LobbyView


@dataclass(frozen=True, slots=True)
class LobbyActionRejected:
    message: str


@dataclass(frozen=True, slots=True)
class GameStarting:
    lobby: LobbyView


@dataclass(frozen=True, slots=True)
class StateUpdated:
    state: PublicState
    revision: int | None = None


@dataclass(frozen=True, slots=True)
class PlayedCardView:
    player_id: PlayerID
    player_name: str
    card_value: int


@dataclass(frozen=True, slots=True)
class CardsRevealed:
    plays: tuple[PlayedCardView, ...]
    revision: int | None = None


@dataclass(frozen=True, slots=True)
class RowChoiceCommitted:
    row_id: RowID
    revision: int | None = None


@dataclass(frozen=True, slots=True)
class ChooseCardRequested:
    player_id: PlayerID
    state: PlayerState
    revision: int | None = None


@dataclass(frozen=True, slots=True)
class ChooseRowRequested:
    player_id: PlayerID
    state: PlayerState
    revision: int | None = None


@dataclass(frozen=True, slots=True)
class DebugStateSnapshot:
    revision: int
    game_state: GameState


class SessionEndReason(StrEnum):
    QUIT = "quit"
    DISCONNECT = "disconnect"
    KICKED = "kicked"
    SERVER_SHUTDOWN = "server_shutdown"
    GAME_FINISHED = "game_finished"


@dataclass(frozen=True, slots=True)
class SessionEnded:
    message: str
    reason: SessionEndReason
    client_id: str | None = None
    display_name: str | None = None


@dataclass(frozen=True, slots=True)
class ServerError:
    message: str


ServerToClientMessage = (
    IdentityAssigned
    | LobbyStateUpdated
    | LobbyActionRejected
    | GameStarting
    | StateUpdated
    | CardsRevealed
    | RowChoiceCommitted
    | ChooseCardRequested
    | ChooseRowRequested
    | DebugStateSnapshot
    | SessionEnded
    | ServerError
)

GameClientMessage = SubmitCard | SubmitRowChoice
RevisionedGameServerMessage = (
    StateUpdated
    | CardsRevealed
    | RowChoiceCommitted
    | ChooseCardRequested
    | ChooseRowRequested
    | DebugStateSnapshot
)
TerminalGameServerMessage = SessionEnded | ServerError
GameServerMessage = RevisionedGameServerMessage | TerminalGameServerMessage


def is_revisioned_game_message(
    message: ServerToClientMessage,
) -> TypeGuard[RevisionedGameServerMessage]:
    return isinstance(
        message,
        (
            StateUpdated,
            CardsRevealed,
            RowChoiceCommitted,
            ChooseCardRequested,
            ChooseRowRequested,
            DebugStateSnapshot,
        ),
    )


def get_game_message_revision(message: ServerToClientMessage) -> int | None:
    if is_revisioned_game_message(message):
        return message.revision
    return None
