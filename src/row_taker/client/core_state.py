from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.trick_presentation_resolver import TrickPresentationState
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import CardsRevealed, LobbyView


class ClientMode(StrEnum):
    LOBBY = "lobby"
    GAME = "game"
    ENDED = "ended"


class PendingAction(StrEnum):
    NONE = "none"
    LOBBY_COMMAND = "lobby_command"
    CHOOSE_CARD = "choose_card"
    CHOOSE_ROW = "choose_row"


@dataclass(frozen=True, slots=True)
class ClientCoreState:
    own_client_id: str | None = None
    own_player_id: PlayerID | None = None
    lobby_view: LobbyView | None = None
    public_state: PublicState | None = None
    player_state: PlayerState | None = None
    session_error: str | None = None
    revealed_trick: CardsRevealed | None = None
    trick_presentation_state: TrickPresentationState | None = None
    presentation_steps: tuple[PresentationStep, ...] = ()
    pending_presentation_steps: tuple[PresentationStep, ...] = ()
    received_game_revision: int | None = None
    applied_game_revision: int | None = None
    client_mode: ClientMode = ClientMode.LOBBY
    pending_action: PendingAction = PendingAction.LOBBY_COMMAND


def initial_client_core_state(own_client_id: str | None = None) -> ClientCoreState:
    return ClientCoreState(own_client_id=own_client_id)
