from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.state import PlayerState, PublicState


@dataclass(frozen=True, slots=True)
class LobbyParticipantView:
    client_id: str
    display_name: str
    participant_kind: str
    seat_index: int | None
    endpoint: str | None = None


@dataclass(frozen=True, slots=True)
class LobbySeatView:
    seat_index: int
    occupant_client_id: str | None
    occupant_display_name: str | None
    occupant_kind: str | None
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


@dataclass(frozen=True, slots=True)
class PlayedCardView:
    player_id: PlayerID
    player_name: str
    card_value: int


@dataclass(frozen=True, slots=True)
class CardsRevealed:
    played_cards: tuple[PlayedCardView, ...]


@dataclass(frozen=True, slots=True)
class RowChoiceCommitted:
    row_id: RowID


@dataclass(frozen=True, slots=True)
class ChooseCardRequested:
    player_id: PlayerID
    state: PlayerState


@dataclass(frozen=True, slots=True)
class ChooseRowRequested:
    player_id: PlayerID
    state: PlayerState


class SessionEndReason(StrEnum):
    QUIT = "quit"
    DISCONNECT = "disconnect"
    KICKED = "kicked"


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
    | SessionEnded
    | ServerError
)

GameClientMessage = SubmitCard | SubmitRowChoice
GameServerMessage = StateUpdated | CardsRevealed | RowChoiceCommitted | ChooseCardRequested | ChooseRowRequested
