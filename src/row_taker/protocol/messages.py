from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.state import DeltaPublicState, PlayerState, PublicState


@dataclass(frozen=True, slots=True)
class LobbyParticipantView:
    client_id: str
    display_name: str
    participant_kind: str
    seat_index: int | None


@dataclass(frozen=True, slots=True)
class LobbySeatView:
    seat_index: int
    occupant_client_id: str | None
    occupant_display_name: str | None
    occupant_kind: str | None


@dataclass(frozen=True, slots=True)
class LobbyView:
    seat_count: int
    participants: tuple[LobbyParticipantView, ...]
    seats: tuple[LobbySeatView, ...]
    game_started: bool


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
class SubmitCard:
    player_id: PlayerID
    card_value: int


@dataclass(frozen=True, slots=True)
class SubmitRowChoice:
    player_id: PlayerID
    row_id: RowID


ClientToServerMessage = (
    JoinLobby
    | SetDisplayName
    | AssignSeatToClient
    | CreateLocalBotOnSeat
    | ClearSeat
    | RequestStartGame
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
class TrickRevealed:
    state: PublicState
    played_cards: tuple[PlayedCardView, ...]
    active_player_id: PlayerID | None = None
    pending_card_value: int | None = None


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
    IdentityAssigned
    | LobbyStateUpdated
    | LobbyActionRejected
    | GameStarting
    | StateUpdated
    | TrickRevealed
    | ChooseCardRequested
    | ChooseRowRequested
    | TrickResolved
    | ServerError
)

GameClientMessage = SubmitCard | SubmitRowChoice
GameServerMessage = StateUpdated | TrickRevealed | ChooseCardRequested | ChooseRowRequested | TrickResolved
